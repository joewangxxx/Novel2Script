import hashlib
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_YAML_PATH = ROOT / "docs/blackboard/state.yaml"


def test_contract_is_frozen_and_unaltered():
    assert STATE_YAML_PATH.exists(), f"Blackboard state file not found at {STATE_YAML_PATH}"
    
    # 读取 state.yaml
    state_data = yaml.safe_load(STATE_YAML_PATH.read_text(encoding="utf-8"))
    
    # 提取 contract_status
    contract_status = state_data.get("contract_status", {})
    assert contract_status, "contract_status is missing in state.yaml"
    
    # 1. 验证契约状态必须为 frozen 冻结状态
    assert contract_status.get("state") == "frozen", "Contract state must be frozen"
    assert contract_status.get("frozen_at") is not None, "frozen_at must be populated when frozen"
    
    # 2. 验证所有的 current_contract 定义项都标记为 frozen
    current_contract = contract_status.get("current_contract", "")
    assert current_contract, "current_contract summary string is missing"
    
    # 拆分并验证每个契约是否带 frozen
    for part in current_contract.split(";"):
        part = part.strip()
        if part:
            assert "frozen" in part, f"Contract definition '{part}' is not marked as frozen"
            
    # 3. 验证 frozen_hashes 是否存在且完整
    frozen_hashes = contract_status.get("frozen_hashes", {})
    assert isinstance(frozen_hashes, dict), "frozen_hashes must be a dictionary"
    assert len(frozen_hashes) >= 20, f"Expected at least 20 schemas in frozen_hashes, got {len(frozen_hashes)}"
    
    # 4. 逐一验证 schema 文件哈希，实现防静默篡改
    for relative_path, expected_hash in frozen_hashes.items():
        file_path = ROOT / relative_path
        assert file_path.exists(), f"Schema file not found at: {file_path}"
        
        # 计算当前本地文件哈希
        content = file_path.read_bytes()
        calculated_sha = hashlib.sha256(content).hexdigest()
        calculated_hash_str = f"sha256:{calculated_sha}"
        
        # 断言一致性，如果被篡改了，这里会抛出 AssertionError 拦截
        assert calculated_hash_str == expected_hash, (
            f"Silent modification detected! Schema '{relative_path}' has been edited after contract freeze.\n"
            f"Expected: {expected_hash}\n"
            f"Calculated: {calculated_hash_str}\n"
            f"Please register an Architecture Change Request under docs/architecture/change-requests/ "
            f"and update the baseline hash in state.yaml."
        )
