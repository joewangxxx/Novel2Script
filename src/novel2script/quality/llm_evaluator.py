from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from novel2script.io import write_yaml
from novel2script.llm.openai_compatible_provider import (
    ProviderConfigurationError,
    ProviderRuntimeError,
)
from novel2script.llm.router import LLMRouter
from novel2script.llm.types import LLMRequest


AGENT_ID = "quality_evaluator"


def run_llm_quality_evaluator(
    screenplay_doc: dict[str, Any],
    *,
    router: LLMRouter | None = None,
    dry_run: bool = True,
    run_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate screenplay dialogue naturalness, goal clarity, and conflict intensity using LLM."""
    if dry_run:
        # Dry-run mode: returns stable mock scores
        scores = {
            "dialogue_naturalness": {
                "score": 92,
                "summary": "对白口语化及历史符合度良好，部分行文可精简。",
                "reasoning": "对白契合历史氛围，无明显出戏的现代词汇。建议个别过长对白作进一步提炼。",
            },
            "character_goal_clarity": {
                "score": 88,
                "summary": "绝大部分场景目标清晰，动作外化程度高。",
                "reasoning": "各 Scene 与 Beat 中人物目的性明确，外化动作充分，角色内驱力合理。",
            },
            "dramatic_conflict_intensity": {
                "score": 85,
                "summary": "戏剧冲突设计有效，动作与对白具有良好张力。",
                "reasoning": "招兵与结义等核心场景中冲突设计有效，可以通过更精细的戏剧化设计进一步放大阻碍。",
            },
        }
        if run_log_path:
            write_yaml(
                {
                    "llm_run_records": [],
                    "errors": [],
                    "notes": ["Dry run evaluation completed without network call."],
                },
                run_log_path,
            )
        return scores

    # Prepare prompt with serializing screenplay structure
    screenplay_yaml = yaml.safe_dump(
        screenplay_doc, allow_unicode=True, sort_keys=False
    )
    prompt = f"""你是一名专业的剧本质量评估专家。请对以下 Novel2Script 改编剧本草案进行评估打分。
评估维度与打分规则（分数范围 0 - 100 整数）：
1. dialogue_naturalness (对白自然度): 评估角色对白是否口语化、符合人物性格与历史背景，是否存在书面语或过长的说明性对白。
2. character_goal_clarity (角色目标清晰度): 评估剧本中各节拍(beat)中角色的具体目标(objective)是否清晰、外化。
3. dramatic_conflict_intensity (戏剧冲突强度): 评估剧本中各场景的戏剧冲突(conflict)和阻碍是否足够强烈，是否流于平淡。

请返回符合以下 JSON 格式的输出，不要包含 Markdown 格式标记：
{{
  "dialogue_naturalness": {{
    "score": 整数分值,
    "summary": "简明扼要的评估总结，限50字内",
    "reasoning": "详细的打分原因与分析"
  }},
  "character_goal_clarity": {{
    "score": 整数分值,
    "summary": "简明扼要的评估总结，限50字内",
    "reasoning": "详细的打分原因与分析"
  }},
  "dramatic_conflict_intensity": {{
    "score": 整数分值,
    "summary": "简明扼要的评估总结，限50字内",
    "reasoning": "详细的打分原因与分析"
  }}
}}

剧本草案 YAML 内容：
{screenplay_yaml}
"""

    request = LLMRequest(
        agent_id=AGENT_ID,
        prompt=prompt,
        temperature=0.1,
        system_prompt="你是一个严谨且专业的剧本评估助手，必须按指定的 JSON 契约返回分析数据。",
    )

    try:
        r = router or LLMRouter.from_environment(allow_network=True)
        result = r.dispatch(request)
        response_text = result.response.text
        
        # Redact secrets/prompts and store metadata run-record in run_log
        if run_log_path:
            record = result.run_record
            redacted_record = {
                "prompt_hash": hashlib_string(prompt),
                "stored_prompt": False,
                "response_text_hash": hashlib_string(response_text),
                "stored_response_text": False,
                "metadata": record.get("metadata", {}),
                "usage": record.get("usage", {}),
            }
            write_yaml({"llm_run_records": [redacted_record]}, run_log_path)

        scores = parse_quality_scores_json(response_text)
        return scores
    except (ProviderConfigurationError, ProviderRuntimeError, Exception) as exc:
        # Fallback gracefully with error indicator and default mock scores
        scores = {
            "dialogue_naturalness": {
                "score": 70,
                "summary": f"评估异常降级: {str(exc)[:50]}",
                "reasoning": f"由于 LLM 评估过程中遇到服务级报错而安全降级：{str(exc)}",
            },
            "character_goal_clarity": {
                "score": 70,
                "summary": f"评估异常降级: {str(exc)[:50]}",
                "reasoning": f"由于 LLM 评估过程中遇到服务级报错而安全降级：{str(exc)}",
            },
            "dramatic_conflict_intensity": {
                "score": 70,
                "summary": f"评估异常降级: {str(exc)[:50]}",
                "reasoning": f"由于 LLM 评估过程中遇到服务级报错而安全降级：{str(exc)}",
            },
        }
        if run_log_path:
            write_yaml(
                {
                    "llm_run_records": [],
                    "errors": [
                        {"code": "quality_eval_llm_failed", "message": str(exc)}
                    ],
                },
                run_log_path,
            )
        return scores


def parse_quality_scores_json(text: str) -> dict[str, Any]:
    """Extract and parse quality scores JSON from LLM response."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    
    # Try cleaning trailing commas
    import re
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    parsed = json.loads(text)
    
    # Validate fields structure to avoid schema violations downstream
    validated = {}
    for key in ("dialogue_naturalness", "character_goal_clarity", "dramatic_conflict_intensity"):
        val = parsed.get(key, {})
        validated[key] = {
            "score": int(val.get("score", 90)),
            "summary": str(val.get("summary", "LLM 评估未附带概述。")),
            "reasoning": str(val.get("reasoning", "LLM 评估未附带推理详情。")),
        }
    return validated


def hashlib_string(val: str) -> str:
    import hashlib
    return hashlib.sha256(val.encode("utf-8")).hexdigest()
