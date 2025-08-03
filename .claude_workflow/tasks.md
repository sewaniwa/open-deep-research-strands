# タスク化: Medium Priority Code Quality Improvements

前段階の`.claude_workflow/design.md`を読み込みました。

## タスク実行順序と優先順位

### フェーズ1: 設定外部化 (Configuration Extraction)
**優先度: 高** | **推定時間: 45分**

#### Task 1.1: agent_settings.py 拡張 (15分)
- [ ] `get_swarm_settings()` メソッド追加
- [ ] `get_communication_settings()` メソッド追加
- [ ] デフォルト値辞書にswarm/communication設定を追加
- [ ] 環境変数対応を追加

#### Task 1.2: swarm_controller.py 設定移行 (15分)  
- [ ] ハードコード値を設定システムから取得に変更
  - `task_timeout = 300` → 設定から取得
  - `effort_times` 辞書 → 設定から取得
  - confidence score固定値 → 設定から取得
- [ ] LoggerMixin継承追加

#### Task 1.3: communication コンポーネント設定移行 (15分)
- [ ] message_router.py: retry_delay, dead_letter_ttl を設定から取得
- [ ] agent_communication.py: timeout値を設定から取得  
- [ ] 両ファイルにLoggerMixin継承追加

### フェーズ2: 入力検証強化 (Input Validation Enhancement)  
**優先度: 高** | **推定時間: 60分**

#### Task 2.1: validation_schemas.py 作成 (30分)
- [ ] JSONSchemaベースの検証システム実装
- [ ] supervisor_agent用スキーマ定義
- [ ] report_agent用スキーマ定義
- [ ] バリデーションデコレータ実装
- [ ] カスタムエラーメッセージ機能

#### Task 2.2: エージェント入力検証追加 (30分)
- [ ] supervisor_agent.py: conduct_research メソッドに包括的検証
- [ ] report_agent.py: 必須フィールド検証強化
- [ ] error_handler.py: 関数名不整合修正 (execute_func → handler)

### フェーズ3: 構造化ログ強化 (Structured Logging Enhancement)
**優先度: 中** | **推定時間: 45分**

#### Task 3.1: LoggerMixin 全面活用 (20分)
- [ ] swarm_controller.py: 構造化ログ追加
- [ ] message_router.py: エラーログ強化  
- [ ] agent_communication.py: ログ追加

#### Task 3.2: エラーハンドリングログ強化 (15分)
- [ ] error_handler.py: 構造化エラーログ追加
- [ ] コンテキスト情報の充実
- [ ] パフォーマンス測定ログ追加

#### Task 3.3: エージェントログ改善 (10分)
- [ ] supervisor_agent.py: ログコンテキスト改善
- [ ] report_agent.py: ログ追加

### フェーズ4: 統合テスト (Integration Testing)
**優先度: 高** | **推定時間: 30分**

#### Task 4.1: 回帰テスト (15分)
- [ ] 既存テストスイート実行
- [ ] test_phase2_integration.py 実行
- [ ] エラー・失敗の解決

#### Task 4.2: 新機能テスト (10分)  
- [ ] 新しい設定値の動作確認
- [ ] 入力検証の動作確認
- [ ] ログ出力の確認

#### Task 4.3: コミット・プッシュ (5分)
- [ ] 変更内容のコミット
- [ ] リモートリポジトリへのプッシュ
- [ ] 最終確認

## 詳細タスク仕様

### Task 1.1: agent_settings.py 拡張

**ファイル**: `configs/agent_settings.py`

**修正内容**:
```python
# _load_defaults メソッドに追加
"swarm_settings": {
    "task_timeout": int(os.getenv("SWARM_TASK_TIMEOUT", "300")),
    "effort_multipliers": {
        "low": float(os.getenv("SWARM_EFFORT_LOW", "1.0")),
        "medium": float(os.getenv("SWARM_EFFORT_MEDIUM", "2.0")),
        "high": float(os.getenv("SWARM_EFFORT_HIGH", "3.0"))
    },
    "confidence_thresholds": {
        "high_relevance": float(os.getenv("SWARM_CONFIDENCE_HIGH", "0.9")),
        "medium_relevance": float(os.getenv("SWARM_CONFIDENCE_MEDIUM", "0.85")),
        "default_confidence": float(os.getenv("SWARM_CONFIDENCE_DEFAULT", "0.85"))
    }
},
"communication_settings": {
    "retry_delay": float(os.getenv("COMM_RETRY_DELAY", "5.0")),
    "dead_letter_ttl": int(os.getenv("COMM_DEAD_LETTER_TTL", "3600")),
    "dequeue_timeout": float(os.getenv("COMM_DEQUEUE_TIMEOUT", "0.1")),
    "error_backoff": float(os.getenv("COMM_ERROR_BACKOFF", "1.0"))
}

# 新メソッド追加
def get_swarm_settings(self) -> Dict[str, Any]:
    """Get swarm controller settings."""
    return self.get("swarm_settings", {})

def get_communication_settings(self) -> Dict[str, Any]:  
    """Get communication settings."""
    return self.get("communication_settings", {})
```

### Task 2.1: validation_schemas.py 作成

**ファイル**: `src/config/validation_schemas.py` (新規作成)

**実装内容**:
- JSONSchemaベースの検証システム
- デコレータパターンでの検証統合
- 分かりやすいエラーメッセージ
- パフォーマンス最適化

### Task 3.1: LoggerMixin 全面活用

**対象ファイル**: 
- `src/workflows/swarm_controller.py`
- `src/communication/message_router.py`  
- `src/communication/agent_communication.py`

**修正パターン**:
```python
from ..config.logging_config import LoggerMixin

class ExampleClass(ExistingBase, LoggerMixin):
    async def method_example(self, param):
        self.log_method_entry("method_example", param_info=str(param))
        try:
            result = await self._process(param)
            self.logger.info("Operation completed", 
                           method="method_example",
                           result_type=type(result).__name__)
            return result
        except Exception as e:
            self.logger.error("Operation failed",
                            method="method_example",
                            error_type=type(e).__name__,
                            error_message=str(e))
            raise
```

## リスク管理

### 高リスクタスク
- **Task 1.2, 1.3**: 設定移行時の既存機能への影響
- **Task 2.2**: 入力検証追加による既存APIの動作変更
- **Task 4.1**: 既存テストの失敗

### 軽減策
- 各タスク完了時に基本的な動作確認
- デフォルト値の確実な設定でフォールバック
- 段階的実装による影響範囲の限定

## 成功基準

### 各フェーズの成功基準
1. **フェーズ1**: ハードコード値の100%設定移行、既存機能の正常動作
2. **フェーズ2**: 全入力検証の動作確認、エラーメッセージの適切性
3. **フェーズ3**: 構造化ログの出力確認、デバッグ情報の充実
4. **フェーズ4**: 全テストパス、パフォーマンス影響の許容範囲内

### 最終成功基準
- [ ] 既存テストスイート 100% パス
- [ ] 新機能の動作確認完了
- [ ] ハードコード値の設定移行 100% 完了
- [ ] 構造化ログの統一された出力
- [ ] パフォーマンス劣化なし

## 実行準備

次の実行フェーズでは、上記タスクを順序通りに実行し、各タスク完了時に進捗を報告する。