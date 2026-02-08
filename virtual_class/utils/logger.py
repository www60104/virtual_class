"""
Utilities - Conversation Logger
對話日誌管理與文字檔匯出功能
"""
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path


class ConversationLogger:
    """
    對話記錄器
    - 匯出完整對話文字檔
    - 支援 Markdown 和 TXT 格式
    """
    
    def __init__(self, export_dir: str = "./exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True, parents=True)
    
    def export_session_transcript(
        self,
        session_uuid: str,
        transcripts: List[dict],
        format: str = "markdown"
    ) -> str:
        """
        匯出 Session 的完整轉錄記錄
        
        Args:
            session_uuid: Session UUID
            transcripts: 轉錄記錄列表（包含 speaker, text, timestamp）
            format: 輸出格式（"markdown" 或 "txt"）
        
        Returns:
            匯出檔案的路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "markdown":
            filename = f"{session_uuid}_{timestamp}.md"
            content = self._generate_markdown(session_uuid, transcripts)
        else:
            filename = f"{session_uuid}_{timestamp}.txt"
            content = self._generate_text(session_uuid, transcripts)
        
        filepath = self.export_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"[Logger] Exported transcript to: {filepath}")
        return str(filepath)
    
    def _generate_markdown(self, session_uuid: str, transcripts: List[dict]) -> str:
        """生成 Markdown 格式的轉錄文字"""
        lines = [
            f"# 對話記錄 - {session_uuid}",
            f"",
            f"**匯出時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**總對話數**: {len(transcripts)} 則",
            f"",
            "---",
            ""
        ]
        
        for i, t in enumerate(transcripts, 1):
            speaker = "👨‍🏫 **老師**" if t["speaker"] == "user" else "👨‍🎓 **學生**"
            timestamp = t.get("timestamp", "")
            text = t.get("text", "")
            source = t.get("source", "unknown")
            
            lines.append(f"### #{i} {speaker}")
            lines.append(f"**時間**: {timestamp}")
            lines.append(f"**來源**: {source}")
            lines.append(f"")
            lines.append(f"{text}")
            lines.append(f"")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_text(self, session_uuid: str, transcripts: List[dict]) -> str:
        """生成純文字格式的轉錄文字"""
        lines = [
            f"對話記錄 - {session_uuid}",
            f"=" * 60,
            f"匯出時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"總對話數: {len(transcripts)} 則",
            f"",
            ""
        ]
        
        for i, t in enumerate(transcripts, 1):
            speaker = "[老師]" if t["speaker"] == "user" else "[學生]"
            timestamp = t.get("timestamp", "")
            text = t.get("text", "")
            
            lines.append(f"#{i} {speaker} ({timestamp})")
            lines.append(f"{text}")
            lines.append("")
            lines.append("-" * 60)
            lines.append("")
        
        return "\n".join(lines)
