#!/usr/bin/env python3
"""
Open Deep Research Strands - 基本的な研究実行例

このスクリプトは、ローカル環境でマルチエージェント研究システムを
実際に使用する方法を示します。
"""
import asyncio
import sys
import os
import time
from pathlib import Path

# プロジェクトパスを追加
project_root = Path(__file__).parent / "open_deep_research_strands"
sys.path.insert(0, str(project_root))

# 環境変数の設定 (APIキーが設定されていない場合はモックモードで実行)
if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
    print("⚠️  APIキーが設定されていません。モックモードで実行します。")
    print("   実際のLLMを使用するには、.envファイルでAPIキーを設定してください。")
    os.environ["MOCK_MODE"] = "true"

from src.agents.supervisor_agent import SupervisorAgent


async def conduct_research_example():
    """研究システムの基本使用例"""
    
    print("🚀 Open Deep Research Strands - 研究システム開始")
    print("=" * 60)
    
    try:
        # 1. SupervisorAgentを初期化
        print("🤖 研究システム初期化中...")
        supervisor = SupervisorAgent()
        await supervisor.initialize()
        print(f"✅ 研究システム初期化完了: {supervisor.agent_id}")
        
        # 2. 研究クエリを設定
        research_queries = [
            "人工知能の医療分野への応用",
            "再生可能エネルギーの最新動向", 
            "ブロックチェーン技術の金融業界への影響"
        ]
        
        print(f"\n📚 利用可能な研究トピック:")
        for i, query in enumerate(research_queries, 1):
            print(f"   {i}. {query}")
        
        # ユーザー入力またはデフォルト選択
        try:
            choice = input(f"\n研究したいトピックを選択してください (1-{len(research_queries)}, Enter=1): ").strip()
            if not choice:
                choice = "1"
            selected_query = research_queries[int(choice) - 1]
        except (ValueError, IndexError):
            selected_query = research_queries[0]
            print(f"⚠️  無効な選択です。デフォルト研究を実行します。")
        
        print(f"\n🔍 研究開始: {selected_query}")
        print("-" * 60)
        
        # 3. 研究実行時間を計測
        start_time = time.time()
        
        # 完全なエンドツーエンド研究ワークフロー
        final_report = await supervisor.conduct_research(selected_query)
        
        execution_time = time.time() - start_time
        
        # 4. 結果を表示
        print("\n" + "="*60)
        print("📊 研究結果")
        print("="*60)
        
        # 基本情報
        print(f"📝 タイトル: {final_report.get('title', 'N/A')}")
        print(f"⏱️  実行時間: {execution_time:.2f}秒")
        print(f"📄 レポートセクション数: {len(final_report.get('report_content', {}).get('sections', {}))}")
        print(f"📚 総ソース数: {final_report.get('metadata', {}).get('total_sources', 0)}")
        
        # ワークフローメタデータ
        workflow_metadata = final_report.get('workflow_metadata', {})
        if workflow_metadata:
            print(f"🔄 完了フェーズ: {', '.join(workflow_metadata.get('phases_completed', []))}")
            print(f"🆔 セッションID: {workflow_metadata.get('session_id', 'N/A')}")
        
        # 品質スコア
        quality_check = final_report.get('quality_check', {})
        if quality_check:
            print(f"🎯 品質スコア: {quality_check.get('quality_score', 0):.2f}")
        
        # エグゼクティブサマリーを表示
        executive_summary = final_report.get('report_content', {}).get('sections', {}).get('executive_summary', {})
        if executive_summary:
            print(f"\n📋 エグゼクティブサマリー:")
            print("-" * 40)
            summary_content = executive_summary.get('content', 'N/A')
            # 適切な長さで表示
            if len(summary_content) > 800:
                print(summary_content[:800] + "...")
                print(f"   [要約は{len(summary_content)}文字、表示は800文字まで]")
            else:
                print(summary_content)
        
        # 主要な発見を表示
        key_findings = final_report.get('key_findings', [])
        if key_findings:
            print(f"\n🔍 主要な発見 (上位3件):")
            print("-" * 40)
            for i, finding in enumerate(key_findings[:3], 1):
                print(f"{i}. {finding}")
        
        # レポートファイルを保存
        output_dir = Path("research_outputs")
        output_dir.mkdir(exist_ok=True)
        
        formatted_reports = final_report.get('formatted_reports', {})
        saved_files = []
        
        for format_name, content in formatted_reports.items():
            if format_name in ['markdown', 'json', 'html']:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                safe_query = "".join(c for c in selected_query if c.isalnum() or c in ' -_').strip()[:30]
                filename = f"{safe_query}_{timestamp}.{format_name}"
                filepath = output_dir / filename
                
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    saved_files.append(str(filepath))
                except Exception as e:
                    print(f"⚠️  ファイル保存エラー ({format_name}): {e}")
        
        if saved_files:
            print(f"\n💾 レポートファイル保存完了:")
            for filepath in saved_files:
                print(f"   - {filepath}")
        
        # システム状態を表示
        status = supervisor.get_session_status()
        print(f"\n🔧 システム状態:")
        print(f"   - アクティブセッション: {status.get('supervisor_status', {}).get('total_sessions', 0)}")
        print(f"   - 現在のフェーズ: {status.get('supervisor_status', {}).get('current_phase', 'N/A')}")
        
        print("\n✅ 研究完了!")
        print("=" * 60)
        
        return final_report
        
    except KeyboardInterrupt:
        print(f"\n⏸️  研究が中断されました。")
        return None
        
    except Exception as e:
        print(f"\n❌ 研究実行中にエラーが発生しました:")
        print(f"   エラー: {str(e)}")
        print(f"   タイプ: {type(e).__name__}")
        
        # デバッグ情報
        print(f"\n🔍 デバッグ情報:")
        print(f"   - Python バージョン: {sys.version}")
        print(f"   - 作業ディレクトリ: {os.getcwd()}")
        print(f"   - プロジェクトパス: {project_root}")
        
        # トラブルシューティングのヒント
        print(f"\n💡 トラブルシューティング:")
        print(f"   1. APIキーが正しく設定されているか確認してください")
        print(f"   2. 依存関係が正しくインストールされているか確認してください")
        print(f"   3. 統合テスト (test_phase2_integration.py) を実行してみてください")
        
        return None


async def interactive_research():
    """インタラクティブな研究セッション"""
    
    print("🎯 インタラクティブ研究モード")
    print("=" * 60)
    
    supervisor = SupervisorAgent()
    await supervisor.initialize()
    
    while True:
        try:
            query = input("\n研究したいトピックを入力してください (quit で終了): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q', '終了']:
                print("👋 研究セッションを終了します。")
                break
                
            if not query:
                print("⚠️  研究トピックを入力してください。")
                continue
            
            print(f"\n🔍 研究実行中: {query}")
            
            try:
                result = await supervisor.conduct_research(query)
                
                # 簡潔な結果表示
                print(f"✅ 研究完了!")
                print(f"   - セクション数: {len(result.get('report_content', {}).get('sections', {}))}")
                print(f"   - 品質スコア: {result.get('quality_check', {}).get('quality_score', 0):.2f}")
                
                # ファイル保存
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"research_output/interactive_{timestamp}.md"
                os.makedirs("research_output", exist_ok=True)
                
                formatted_reports = result.get('formatted_reports', {})
                if 'markdown' in formatted_reports:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(formatted_reports['markdown'])
                    print(f"   - レポート保存: {filename}")
                
            except Exception as e:
                print(f"❌ 研究エラー: {str(e)}")
                
        except KeyboardInterrupt:
            print(f"\n👋 研究セッションを終了します。")
            break


def main():
    """メイン実行関数"""
    
    print("🌟 Open Deep Research Strands へようこそ!")
    print("=" * 60)
    print("このシステムは、マルチエージェントアーキテクチャを使用して")
    print("包括的な研究レポートを自動生成します。")
    print("=" * 60)
    
    # モード選択
    print("\n実行モードを選択してください:")
    print("1. 基本研究例 (推奨)")
    print("2. インタラクティブモード")
    print("3. システム終了")
    
    try:
        mode = input("\nモードを選択 (1-3, Enter=1): ").strip()
        if not mode:
            mode = "1"
            
        if mode == "1":
            asyncio.run(conduct_research_example())
        elif mode == "2":
            asyncio.run(interactive_research())
        elif mode == "3":
            print("👋 システムを終了します。")
        else:
            print("⚠️  無効な選択です。基本研究例を実行します。")
            asyncio.run(conduct_research_example())
            
    except KeyboardInterrupt:
        print(f"\n👋 システムを終了します。")
    except Exception as e:
        print(f"\n❌ システムエラー: {str(e)}")


if __name__ == "__main__":
    main()