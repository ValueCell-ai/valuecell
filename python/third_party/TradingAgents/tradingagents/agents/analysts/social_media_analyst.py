from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Check if ticker is A-share stock
        is_a_share = (
            ticker.isdigit()
            and len(ticker) == 6
            and ticker[0] in ['0', '3', '6', '8']
        )

        if toolkit.config["online_tools"]:
            if is_a_share:
                # Use A-share sentiment tools for Chinese stocks
                tools = [
                    toolkit.get_a_share_guba_sentiment,
                    toolkit.get_a_share_news,
                ]
            else:
                # Use US stock sentiment tools
                tools = [toolkit.get_stock_news_openai]
        else:
            if is_a_share:
                # Use A-share sentiment tools (offline mode)
                tools = [
                    toolkit.get_a_share_guba_sentiment,
                ]
            else:
                # Use US stock sentiment tools (offline mode)
                tools = [
                    toolkit.get_reddit_stock_info,
                ]

        # Adjust system message based on market
        if is_a_share:
            system_message = (
                "You are a social media and sentiment analyst for A-share (Chinese stock market) companies. "
                "Your task is to analyze public sentiment and social media discussions about the company. "
                "Please write a comprehensive report covering: "
                "1) East Money Guba (股吧) sentiment and discussion trends - analyze what retail investors are saying "
                "2) Hot discussion topics and their sentiment (bullish, bearish, or neutral) "
                "3) Analysis of post engagement (reads, comments) to gauge investor interest "
                "4) Recent news sentiment and its impact on public perception. "
                "Do not simply state the trends are mixed, provide detailed and fine-grained analysis and insights that may help traders make decisions. "
                "Note: Guba is similar to Reddit for US stocks - it's where Chinese retail investors discuss stocks."
                + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.""",
            )
        else:
            system_message = (
                "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + """ Make sure to append a Makrdown table at the end of the report to organize key points in the report, organized and easy to read.""",
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
                    "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
