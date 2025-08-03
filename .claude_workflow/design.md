# 設計: Medium Priority Code Quality Improvements

前段階の`.claude_workflow/requirements.md`を読み込みました。

## アプローチ検討

### 1. 段階的改善アプローチ
既存の優秀なアーキテクチャを活用し、段階的に改善を実施する。
- 既存の`AgentSettings`クラスと`LoggerMixin`を最大限活用
- 新機能追加より既存機能の強化に重点
- 後方互換性を保ちながら改善

### 2. 設定管理の設計方針
- 既存の`agent_settings.py`を拡張してハードコード値を管理
- 環境変数による設定オーバーライド機能を維持
- 新しい設定カテゴリを追加（swarm, communication）

### 3. 入力検証の設計方針
- JSONSchemaベースの検証システム導入
- 既存の`validate_task_data`メソッドを拡張
- バリデーションエラーの一貫したハンドリング

### 4. ログ強化の設計方針
- 既存の`LoggerMixin`の活用を全面的に推進
- 構造化ログによるエラーコンテキスト強化
- パフォーマンス測定ログの統合

## 実施手順決定

### フェーズ1: 設定外部化 (Configuration Extraction)
1. `agent_settings.py`に新しい設定カテゴリを追加
2. ハードコード値を設定に移行
3. 各コンポーネントで設定システムを活用

### フェーズ2: 入力検証強化 (Input Validation Enhancement)
1. `validation_schemas.py`を作成
2. JSONSchemaによる検証システム実装
3. 各エージェントに包括的な検証を追加

### フェーズ3: ログ強化 (Structured Logging Enhancement)
1. 全コンポーネントに`LoggerMixin`を適用
2. エラーハンドリングでの構造化ログ強化
3. パフォーマンス測定ログの追加

### フェーズ4: 統合テスト (Integration Testing)
1. 既存テストの実行による回帰確認
2. 新機能のテスト
3. パフォーマンス影響の測定

## 問題点の特定

### 1. 設定管理における課題
- **課題**: ハードコード値の分散
- **影響**: 運用時の設定変更が困難
- **解決策**: 中央集権的な設定管理システムの活用

### 2. 入力検証における課題
- **課題**: 検証ロジックの不統一
- **影響**: エラー処理の一貫性不足
- **解決策**: スキーマベース検証の導入

### 3. ログにおける課題
- **課題**: 構造化ログの活用不足
- **影響**: デバッグとモニタリングの効率低下
- **解決策**: LoggerMixinの全面活用

## 詳細設計

### 1. 設定システム拡張設計

#### 新しい設定カテゴリ

```python
# swarm_settings
{
    "task_timeout": 300,
    "effort_multipliers": {
        "low": 1.0,
        "medium": 2.0, 
        "high": 3.0
    },
    "confidence_thresholds": {
        "high_relevance": 0.9,
        "medium_relevance": 0.85,
        "default_confidence": 0.85
    }
}

# communication_settings  
{
    "retry_delay": 5.0,
    "dead_letter_ttl": 3600,
    "dequeue_timeout": 0.1,
    "error_backoff": 1.0
}
```

#### 設定アクセスパターン

```python
# 既存パターンを踏襲
swarm_settings = self.agent_settings.get_swarm_settings()
timeout = swarm_settings.get("task_timeout", 300)
```

### 2. 入力検証システム設計

#### バリデーションスキーマ例

```python
# supervisor_agent input schema
CONDUCT_RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "user_query": {
            "type": "string",
            "minLength": 5,
            "maxLength": 10000
        },
        "parameters": {
            "type": "object",
            "properties": {
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 10},
                "research_depth": {"type": "string", "enum": ["shallow", "medium", "deep"]}
            }
        }
    },
    "required": ["user_query"]
}
```

#### 検証統合パターン

```python
@validate_input(CONDUCT_RESEARCH_SCHEMA)
async def conduct_research(self, user_query: str, parameters: Dict[str, Any] = None):
    # 検証済みの入力で処理実行
```

### 3. ログ強化システム設計

#### LoggerMixin統合パターン

```python
class EnhancedComponent(BaseAgent, LoggerMixin):
    async def critical_operation(self, data):
        self.log_method_entry("critical_operation", input_size=len(data))
        
        try:
            result = await self._process(data)
            self.logger.info("Operation successful", 
                           operation="critical_operation",
                           result_size=len(result))
            return result
        except Exception as e:
            self.logger.error("Operation failed",
                            operation="critical_operation", 
                            error_type=type(e).__name__,
                            error_message=str(e),
                            input_data=data[:100])  # Truncated for safety
            raise
```

## ファイル変更計画

### 既存ファイル修正

1. **`configs/agent_settings.py`**
   - `get_swarm_settings()` メソッド追加
   - `get_communication_settings()` メソッド追加
   - デフォルト値にswarm/communication設定を追加

2. **`src/workflows/swarm_controller.py`**
   - `LoggerMixin` 継承追加
   - ハードコード値を設定システムから取得
   - 構造化ログの追加

3. **`src/communication/message_router.py`**
   - `LoggerMixin` 継承追加
   - 設定システムの活用
   - エラーログの強化

4. **`src/communication/agent_communication.py`**
   - 設定システムからタイムアウト値取得
   - ログ強化

5. **`src/agents/supervisor_agent.py`**
   - 入力検証の強化
   - ログコンテキストの改善

6. **`src/agents/error_handler.py`**
   - 関数名の統一（execute_func → handler）
   - エラーログの構造化強化

7. **`src/agents/report_agent.py`**
   - 入力検証の強化
   - ログの追加

### 新規ファイル作成

1. **`src/config/validation_schemas.py`**
   - 全エージェントの入力検証スキーマ定義
   - バリデーションデコレータ実装
   - カスタムバリデーター関数

## リスク軽減策

### 1. 後方互換性の確保
- デフォルト値の維持
- 既存APIインターフェースの保持
- 段階的な移行

### 2. パフォーマンス影響の最小化
- 検証処理の最適化
- ログレベルによる出力制御
- 必要に応じたキャッシュ活用

### 3. エラーハンドリングの強化
- 設定読み込みエラーの適切な処理
- 検証エラーの分かりやすいメッセージ
- フォールバック機能の実装

## 成功指標

### 1. 定量的指標
- 既存テスト100%パス
- 新規追加設定項目の環境変数対応100%
- ハードコード値の設定移行100%

### 2. 定性的指標
- コードの可読性向上
- 運用時の設定変更容易性
- エラー診断の効率化

## 次のステップ

タスク化フェーズでは、上記設計を実行可能な具体的タスクに分解し、優先順位を設定する。