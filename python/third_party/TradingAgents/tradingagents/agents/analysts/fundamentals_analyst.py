from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Check if ticker is A-share stock (6 digits starting with 0, 3, 6, or 8)
        is_a_share = (
            ticker.isdigit()
            and len(ticker) == 6
            and ticker[0] in ['0', '3', '6', '8']
        )

        if toolkit.config["online_tools"]:
            if is_a_share:
                # Use A-share tools for Chinese stocks
                tools = [
                    toolkit.get_a_share_balance_sheet,
                    toolkit.get_a_share_income_statement,
                    toolkit.get_a_share_cashflow_statement,
                    toolkit.get_a_share_major_holder_trades,
                    toolkit.get_a_share_announcements,
                ]
            else:
                # Use US stock tools
                tools = [toolkit.get_fundamentals_openai]
        else:
            if is_a_share:
                # Use A-share tools for Chinese stocks (offline mode)
                tools = [
                    toolkit.get_a_share_balance_sheet,
                    toolkit.get_a_share_income_statement,
                    toolkit.get_a_share_cashflow_statement,
                    toolkit.get_a_share_major_holder_trades,
                ]
            else:
                # Use US stock tools (offline mode)
                tools = [
                    toolkit.get_finnhub_company_insider_sentiment,
                    toolkit.get_finnhub_company_insider_transactions,
                    toolkit.get_simfin_balance_sheet,
                    toolkit.get_simfin_cashflow,
                    toolkit.get_simfin_income_stmt,
                ]

        # Adjust system message based on market
        if is_a_share:
            system_message = (
                "You are a researcher tasked with analyzing fundamental information about an A-share (Chinese stock market) company. "
                "Please write a comprehensive report of the company's fundamental information including: "
                "1) Financial statements (balance sheet, income statement, cash flow) "
                "2) Major shareholder trading activities (similar to insider trading) "
                "3) Official company announcements "
                "4) Financial ratios and key metrics. "
                "Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and fine-grained analysis and insights that may help traders make decisions. "
                "Note: For A-share stocks, pay special attention to: government policies, major shareholder changes, and regulatory announcements."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.",
            )
        else:
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.",
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
