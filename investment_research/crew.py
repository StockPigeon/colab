"""Investment Research Crew - Main orchestration."""

import os
from pathlib import Path

import yaml
from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool

from .tools import (
    investment_data_tool,
    price_sentiment_data_tool,
    governance_data_tool,
    business_profile_tool,
    key_metrics_tool,
    sec_filings_tool,
    web_search_tool,
    historical_multiples_tool,
    peer_comparison_tool,
    valuation_chart_tool,
)
from .progress_callbacks import create_task_callback


class InvestmentResearchCrew:
    """Investment Research Crew for comprehensive stock analysis."""

    def __init__(self):
        """Initialize the crew with configuration and tools."""
        self.config_dir = Path(__file__).parent / "config"
        self.agents_config = self._load_yaml("agents.yaml")
        self.tasks_config = self._load_yaml("tasks.yaml")
        self.scrape_tool = ScrapeWebsiteTool()

        # Build agents and tasks
        self._agents = self._build_agents()
        self._tasks = self._build_tasks()

    def _load_yaml(self, filename: str) -> dict:
        """Load a YAML configuration file."""
        path = self.config_dir / filename
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _build_agents(self) -> dict:
        """Build all agents from configuration."""
        agents = {}

        # Phase Classifier
        cfg = self.agents_config["phase_classifier"]
        agents["phase_classifier"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[investment_data_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Sentiment Analyst
        cfg = self.agents_config["sentiment_analyst"]
        agents["sentiment_analyst"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[price_sentiment_data_tool, web_search_tool, self.scrape_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Strategist (Moat Analyst)
        cfg = self.agents_config["strategist"]
        agents["strategist"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[investment_data_tool, web_search_tool, sec_filings_tool, self.scrape_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Governance Expert
        cfg = self.agents_config["governance_expert"]
        agents["governance_expert"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[governance_data_tool, sec_filings_tool, web_search_tool, self.scrape_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Quant Auditor
        cfg = self.agents_config["quant_auditor"]
        agents["quant_auditor"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[investment_data_tool, key_metrics_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Business Profile Analyst
        cfg = self.agents_config["business_profile_analyst"]
        agents["business_profile_analyst"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[business_profile_tool, sec_filings_tool],
            verbose=True,
            allow_delegation=False,
        )

        # Scorecard Analyst
        cfg = self.agents_config["scorecard_analyst"]
        agents["scorecard_analyst"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[],  # No tools needed - just aggregates context from other tasks
            verbose=True,
            allow_delegation=False,
        )

        # Valuation Analyst
        cfg = self.agents_config["valuation_analyst"]
        agents["valuation_analyst"] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[historical_multiples_tool, peer_comparison_tool, valuation_chart_tool],
            verbose=True,
            allow_delegation=False,
        )

        return agents

    def _build_tasks(self) -> dict:
        """Build all tasks from configuration."""
        tasks = {}

        # Task: Price & Sentiment
        cfg = self.tasks_config["task_price_sentiment"]
        tasks["task_price_sentiment"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            callback=create_task_callback("task_price_sentiment"),
        )

        # Task: Business Phase
        cfg = self.tasks_config["task_business_phase"]
        tasks["task_business_phase"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            callback=create_task_callback("task_business_phase"),
        )

        # Task: Key Metrics (depends on Business Phase)
        cfg = self.tasks_config["task_key_metrics"]
        tasks["task_key_metrics"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"]],
            callback=create_task_callback("task_key_metrics"),
        )

        # Task: Business Profile (depends on Business Phase)
        cfg = self.tasks_config["task_business_profile"]
        tasks["task_business_profile"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"]],
            callback=create_task_callback("task_business_profile"),
        )

        # Task: Business Moat (depends on Business Phase)
        cfg = self.tasks_config["task_business_moat"]
        tasks["task_business_moat"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"]],
            callback=create_task_callback("task_business_moat"),
        )

        # Task: Execution Risk (depends on Business Phase and Moat)
        cfg = self.tasks_config["task_execution_risk"]
        tasks["task_execution_risk"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"], tasks["task_business_moat"]],
            callback=create_task_callback("task_execution_risk"),
        )

        # Task: Growth Drivers (depends on Business Phase and Moat)
        cfg = self.tasks_config["task_growth_drivers"]
        tasks["task_growth_drivers"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"], tasks["task_business_moat"]],
            callback=create_task_callback("task_growth_drivers"),
        )

        # Task: Management & Risk (depends on Business Phase and Moat)
        cfg = self.tasks_config["task_management_risk"]
        tasks["task_management_risk"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[tasks["task_business_phase"], tasks["task_business_moat"]],
            callback=create_task_callback("task_management_risk"),
        )

        # Task: Visual Valuation (depends on Phase and Moat)
        cfg = self.tasks_config["task_visual_valuation"]
        tasks["task_visual_valuation"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[
                tasks["task_business_phase"],
                tasks["task_business_moat"],
            ],
            callback=create_task_callback("task_visual_valuation"),
        )

        # Task: Quant Valuation (depends on Phase, Moat, Risk, and Visual Valuation)
        cfg = self.tasks_config["task_quant_valuation"]
        tasks["task_quant_valuation"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[
                tasks["task_business_phase"],
                tasks["task_business_moat"],
                tasks["task_management_risk"],
                tasks["task_visual_valuation"],
            ],
            callback=create_task_callback("task_quant_valuation"),
        )

        # Task: Investment Scorecard (aggregates all 10 section scores)
        cfg = self.tasks_config["task_investment_scorecard"]
        tasks["task_investment_scorecard"] = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self._agents[cfg["agent"]],
            context=[
                tasks["task_price_sentiment"],
                tasks["task_business_phase"],
                tasks["task_key_metrics"],
                tasks["task_business_profile"],
                tasks["task_business_moat"],
                tasks["task_execution_risk"],
                tasks["task_growth_drivers"],
                tasks["task_management_risk"],
                tasks["task_visual_valuation"],
                tasks["task_quant_valuation"],
            ],
            callback=create_task_callback("task_investment_scorecard"),
        )

        return tasks

    def get_agent(self, name: str) -> Agent:
        """Get a specific agent by name."""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found. Available: {list(self._agents.keys())}")
        return self._agents[name]

    def get_task(self, name: str) -> Task:
        """Get a specific task by name."""
        if name not in self._tasks:
            raise ValueError(f"Task '{name}' not found. Available: {list(self._tasks.keys())}")
        return self._tasks[name]

    def crew(self) -> Crew:
        """Build and return the full crew."""
        # Order matters for sequential execution
        # Investment Scorecard runs last to aggregate all section scores
        ordered_tasks = [
            self._tasks["task_price_sentiment"],
            self._tasks["task_business_phase"],
            self._tasks["task_key_metrics"],
            self._tasks["task_business_profile"],
            self._tasks["task_business_moat"],
            self._tasks["task_execution_risk"],
            self._tasks["task_growth_drivers"],
            self._tasks["task_management_risk"],
            self._tasks["task_visual_valuation"],
            self._tasks["task_quant_valuation"],
            self._tasks["task_investment_scorecard"],
        ]

        ordered_agents = [
            self._agents["sentiment_analyst"],
            self._agents["phase_classifier"],
            self._agents["business_profile_analyst"],
            self._agents["strategist"],
            self._agents["governance_expert"],
            self._agents["quant_auditor"],
            self._agents["valuation_analyst"],
            self._agents["scorecard_analyst"],
        ]

        return Crew(
            agents=ordered_agents,
            tasks=ordered_tasks,
            process=Process.sequential,
            verbose=True,
        )

    def run_single_task(self, task_name: str, ticker: str):
        """
        Run a single task in isolation for testing.

        Args:
            task_name: Name of the task to run
            ticker: Stock ticker symbol

        Returns:
            CrewOutput from the single-task crew
        """
        task = self.get_task(task_name)

        # Create a mini-crew with just this task
        mini_crew = Crew(
            agents=[task.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        return mini_crew.kickoff(inputs={"ticker": ticker})

    def run_single_agent(self, agent_name: str, ticker: str, prompt: str = None):
        """
        Test a single agent with a simple prompt.

        Args:
            agent_name: Name of the agent to test
            ticker: Stock ticker symbol
            prompt: Custom prompt (optional, uses default if not provided)

        Returns:
            CrewOutput from the single-agent test
        """
        agent = self.get_agent(agent_name)

        if prompt is None:
            prompt = f"Analyze {ticker} using your available tools and provide a brief summary."

        test_task = Task(
            description=prompt,
            expected_output="Brief analysis summary.",
            agent=agent,
        )

        mini_crew = Crew(
            agents=[agent],
            tasks=[test_task],
            process=Process.sequential,
            verbose=True,
        )

        return mini_crew.kickoff(inputs={"ticker": ticker})
