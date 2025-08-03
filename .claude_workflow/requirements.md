# 要件定義: Medium Priority Code Quality Improvements

## 目的の明確化

コードレビューで特定された中優先度の改善項目を実装し、システムの堅牢性、保守性、運用性を向上させる。

### 対象改善項目

1. **包括的な入力検証の追加** (Add more comprehensive input validation)
2. **設定の外部ファイル化** (Extract configuration to external files)  
3. **構造化ログの強化** (Enhance error logging with structured logging)

## 現状把握

### 1. 入力検証の現状
- SupervisorAgent.py:100 でユーザークエリの基本的な検証のみ
- ReportAgent.py:125-131 で必須フィールドの検証が不十分
- 複雑な入力に対するスキーマ検証が未実装
- Error handler の execute_func vs handler の関数名に不整合

### 2. 設定管理の現状
- 既存の設定システムは良好だが、いくつかのハードコード値が残存
- swarm_controller.py でタイムアウト値やエフォート時間がハードコード
- message_router.py で retry_delay, dead_letter_ttl がハードコード
- agent_communication.py でタイムアウト値がハードコード

### 3. ログシステムの現状
- 既存の logging_config.py は structlog をサポートし良好
- しかし、一部のファイルでは構造化ログが完全に活用されていない
- エラーハンドリングでのコンテキスト情報が不足
- パフォーマンス・デバッグ用ログが不十分

## 成功基準

### 1. 入力検証
- [ ] 全ての公開メソッドで適切な入力検証が実装されている
- [ ] JSON/Dict形式の複雑な入力に対するスキーマ検証が動作する
- [ ] 検証エラー時に分かりやすいエラーメッセージが提供される
- [ ] エラーハンドラーの function name の不整合を修正

### 2. 設定管理
- [ ] swarm_controller.py のハードコードされた値を設定に移行
- [ ] message_router.py のハードコードされた値を設定に移行
- [ ] agent_communication.py のハードコードされた値を設定に移行
- [ ] 新しい設定値が agent_settings.py で管理される

### 3. 構造化ログ
- [ ] 全コンポーネントで LoggerMixin の活用を徹底
- [ ] エラー発生時に十分なコンテキスト情報がログに記録される
- [ ] パフォーマンス測定ログの追加
- [ ] 既存の構造化ログ機能を最大限活用

## 対象ファイル

### 主要修正対象
- `src/agents/supervisor_agent.py` - 入力検証強化
- `src/agents/error_handler.py` - 関数名修正、ログ強化
- `src/agents/report_agent.py` - 入力検証強化
- `src/workflows/swarm_controller.py` - 設定外部化、ログ強化
- `src/communication/message_router.py` - 設定外部化
- `src/communication/agent_communication.py` - 設定外部化

### 新規作成ファイル
- `src/config/validation_schemas.py` - 入力検証スキーマ定義

### 設定更新
- `configs/agent_settings.py` - 新しい設定値追加

## 制約条件

- 既存のテストを破壊しない
- 既存のAPIインターフェースを維持する
- パフォーマンスに悪影響を与えない
- 既存の優秀な設定・ログシステムを最大限活用
- CLAUDE.mdワークフローに従って段階的に実装する

## 想定リスク

- 既存機能への影響
- 設定ファイル読み込み時のエラーハンドリング
- ログ出力量の増加によるパフォーマンス影響（既存システムで十分対策済み）

## 特定された改善箇所

### ハードコード値一覧
1. swarm_controller.py:
   - task_timeout = 300
   - effort_times = {"low": 1.0, "medium": 2.0, "high": 3.0}
   - 各種confidence score の固定値

2. message_router.py:
   - retry_delay = 5.0
   - dead_letter_ttl = 3600
   - sleep時間の固定値

3. agent_communication.py:
   - timeout=0.1 の固定値

### 入力検証改善箇所
1. supervisor_agent.py:100 - user_query検証
2. report_agent.py:125-131 - 必須フィールド検証
3. error_handler.py:674 - 関数名不整合の修正