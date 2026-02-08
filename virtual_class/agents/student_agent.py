"""
Agent Layer - Student Agent
虛擬學生 Agent：處理使用者輸入並生成提問
"""
import os
from typing import Optional
from openai import AsyncOpenAI
from agents.prompts import STUDENT_AGENT_PROMPT
from services.gcc_module import GCCModule


class StudentAgent:
    """
    虛擬學生 Agent
    - 接收老師（使用者）的教學內容
    - 生成學生風格的回應和提問
    - 使用 GCC 模組獲取上下文
    """
    
    def __init__(self, gcc_module: GCCModule, model: str = "gpt-4"):
        self.gcc = gcc_module
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def process(
        self,
        session_id: int,
        user_input: str,
        use_qwen_fallback: bool = False
    ) -> str:
        """
        處理使用者輸入，生成學生回應
        
        Args:
            session_id: Session ID
            user_input: 使用者（老師）的教學內容
            use_qwen_fallback: 是否使用 Qwen 作為備用（可選）
        
        Returns:
            學生 agent 的回應文字
        """
        # 獲取簡化上下文（最近 5 輪對話）
        context = await self.gcc.context(session_id, max_turns=5)
        
        # 構建對話歷史
        messages = [
            {"role": "system", "content": STUDENT_AGENT_PROMPT}
        ]
        
        # 添加歷史對話
        for conv in context.get("recent_conversations", []):
            if conv["user"]:
                messages.append({"role": "user", "content": conv["user"]})
            if conv["agent"]:
                messages.append({"role": "assistant", "content": conv["agent"]})
        
        # 添加當前輸入
        messages.append({"role": "user", "content": user_input})
        
        # 調用 LLM
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # 稍高的溫度讓回應更自然
                max_tokens=150
            )
            
            agent_response = response.choices[0].message.content
            
            # 記錄到 GCC
            await self.gcc.log_ota(
                session_id=session_id,
                event_type="student_response",
                data={"user_input": user_input, "agent_response": agent_response},
                agent_type="student"
            )
            
            return agent_response
        
        except Exception as e:
            print(f"[StudentAgent] Error: {e}")
            
            # Fallback 回應
            return "抱歉，我有點不太懂... 可以再說一次嗎？"
