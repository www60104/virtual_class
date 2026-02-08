"""
Core Layer - LangGraph Coordinator
場景協調器：使用 LangGraph 管理 Student/Expert Agent 的狀態機
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator


class AgentState(TypedDict):
    """
    LangGraph 狀態定義
    """
    messages: Annotated[list[BaseMessage], operator.add]  # 對話歷史
    current_agent: Literal["student", "expert", "idle"]  # 當前活躍的 agent
    user_question: str  # 使用者最新問題
    student_response: str  # 學生 agent 回應
    expert_evaluation: str  # 專家 agent 評估
    session_id: int  # Session ID
    turn_count: int  # 對話輪數


class LangGraphCoordinator:
    """
    LangGraph 協調器
    負責：
    1. 定義狀態機（Student Agent → Expert Agent → 結束）
    2. 協調不同 Agent 的執行順序
    3. 管理對話流程
    """
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        構建 LangGraph 狀態機
        
        流程：
        START → Student Agent → (可選) Expert Agent → END
        """
        workflow = StateGraph(AgentState)
        
        # 添加節點
        workflow.add_node("student_agent", self._student_agent_node)
        workflow.add_node("expert_agent", self._expert_agent_node)
        
        # 設定入口點
        workflow.set_entry_point("student_agent")
        
        # 設定邊（條件路由）
        workflow.add_conditional_edges(
            "student_agent",
            self._should_call_expert,
            {
                "expert": "expert_agent",
                "end": END
            }
        )
        
        workflow.add_edge("expert_agent", END)
        
        return workflow.compile()
    
    async def _student_agent_node(self, state: AgentState) -> AgentState:
        """
        Student Agent 節點
        這裡是佔位符，實際邏輯在 agents/student_agent.py
        """
        print(f"[LangGraph] Student Agent processing: {state['user_question']}")
        
        # 這裡應該調用 StudentAgent.process()
        # 暫時使用佔位符
        state["student_response"] = f"Student: I'm thinking about {state['user_question']}"
        state["current_agent"] = "student"
        state["turn_count"] += 1
        
        return state
    
    async def _expert_agent_node(self, state: AgentState) -> AgentState:
        """
        Expert Agent 節點
        僅在需要評估時調用
        """
        print(f"[LangGraph] Expert Agent evaluating student response")
        
        # 這裡應該調用 ExpertAgent.evaluate()
        state["expert_evaluation"] = "Expert: Good approach, consider..."
        state["current_agent"] = "expert"
        
        return state
    
    def _should_call_expert(self, state: AgentState) -> Literal["expert", "end"]:
        """
        決定是否需要 Expert Agent 介入
        條件：每 3 輪對話調用一次 Expert
        """
        if state["turn_count"] % 3 == 0:
            return "expert"
        return "end"
    
    async def process_user_input(
        self,
        session_id: int,
        user_input: str,
        current_state: dict = None
    ) -> dict:
        """
        處理使用者輸入，執行狀態機
        
        Args:
            session_id: Session ID
            user_input: 使用者輸入文字
            current_state: 當前狀態（可選）
        
        Returns:
            更新後的狀態字典
        """
        # 初始化或延續狀態
        if not current_state:
            state: AgentState = {
                "messages": [],
                "current_agent": "idle",
                "user_question": user_input,
                "student_response": "",
                "expert_evaluation": "",
                "session_id": session_id,
                "turn_count": 0
            }
        else:
            state = current_state
            state["user_question"] = user_input
        
        # 添加使用者訊息
        state["messages"].append(HumanMessage(content=user_input))
        
        # 執行狀態機
        result = await self.graph.ainvoke(state)
        
        print(f"[LangGraph] Workflow completed. Current agent: {result['current_agent']}")
        
        return result
    
    def get_current_state(self, state: AgentState) -> dict:
        """返回狀態摘要（用於存入資料庫）"""
        return {
            "current_agent": state["current_agent"],
            "turn_count": state["turn_count"],
            "last_student_response": state["student_response"],
            "last_expert_evaluation": state.get("expert_evaluation", "")
        }
