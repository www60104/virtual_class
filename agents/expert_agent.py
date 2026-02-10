"""
Agent Layer - Expert Agent
專家評估 Agent：評估教學方法論
"""
import os
from openai import AsyncOpenAI
from agents.prompts import EXPERT_AGENT_PROMPT
from services.gcc_module import GCCModule


class ExpertAgent:
    """
    專家評估 Agent
    - 分析老師的教學表現
    - 提供建設性反饋
    - 使用完整上下文（GCC context_full）
    """
    
    def __init__(self, gcc_module: GCCModule, model: str = "gpt-4"):
        self.gcc = gcc_module
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def evaluate(self, session_id: int) -> str:
        """
        評估當前 session 的教學表現
        
        Args:
            session_id: Session ID
        
        Returns:
            專家評估文字
        """
        # 獲取完整上下文
        context_full = await self.gcc.context_full(session_id)
        
        if "error" in context_full:
            return "無法獲取完整上下文，請稍後再試。"
        
        # 構建評估提示
        conversation_summary = self._summarize_conversations(
            context_full.get("conversations", [])
        )
        
        messages = [
            {"role": "system", "content": EXPERT_AGENT_PROMPT},
            {
                "role": "user",
                "content": f"""
請評估以下教學互動：

{conversation_summary}

請根據清晰度、互動性、結構性、適應性四個維度給出評估。
"""
            }
        ]
        
        # 調用 LLM
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # 較低溫度確保評估客觀
                max_tokens=300
            )
            
            evaluation = response.choices[0].message.content
            
            # 記錄到 GCC
            await self.gcc.log_ota(
                session_id=session_id,
                event_type="expert_evaluation",
                data={"evaluation": evaluation},
                agent_type="expert"
            )
            
            return evaluation
        
        except Exception as e:
            print(f"[ExpertAgent] Error: {e}")
            return "評估服務暫時無法使用。"
    
    def _summarize_conversations(self, conversations: list) -> str:
        """將對話歷史格式化為可讀文字"""
        if not conversations:
            return "（尚無對話記錄）"
        
        summary_lines = []
        for i, conv in enumerate(conversations, 1):
            user_msg = conv.get("user_message", "").strip()
            agent_msg = conv.get("agent_response", "").strip()
            
            summary_lines.append(f"輪次 {i}:")
            summary_lines.append(f"  老師: {user_msg}")
            summary_lines.append(f"  學生: {agent_msg}")
            summary_lines.append("")
        
        return "\n".join(summary_lines)
