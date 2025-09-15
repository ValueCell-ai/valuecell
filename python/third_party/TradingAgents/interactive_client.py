#!/usr/bin/env python3
"""
TradingAgents Interactive Client

Provides a friendly interactive interface, supporting:
1. Interactive selection of LLM providers and models
2. Selection of analyst combinations
3. Selection of stock codes
4. Set analysis parameters
5. Real-time view of analysis results
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add project path
project_root = Path(__file__).parent
valuecell_root = project_root.parent.parent / "valuecell"
sys.path.insert(0, str(valuecell_root))

from valuecell.core.agent.connect import RemoteConnections

# Set logging
logging.basicConfig(level=logging.WARNING)  # Reduce logging output
logger = logging.getLogger(__name__)


class TradingAgentsInteractiveClient:
    """TradingAgents interactive client"""
    
    def __init__(self):
        self.connections = RemoteConnections()
        self.agent_name = "TradingAgentsAdapter"
        self.client: Optional[object] = None
        
        # Configuration options
        self.available_tickers = {
            "AAPL": "Apple Inc.",
            "GOOGL": "Alphabet Inc.", 
            "MSFT": "Microsoft Corporation",
            "NVDA": "NVIDIA Corporation",
            "TSLA": "Tesla Inc.",
            "AMZN": "Amazon.com Inc.",
            "META": "Meta Platforms Inc.",
            "NFLX": "Netflix Inc.",
            "SPY": "SPDR S&P 500 ETF"
        }
        
        self.available_analysts = ["market", "social", "news", "fundamentals"]
        
        self.llm_providers = {
            "openai": "OpenAI",
            "anthropic": "Anthropic", 
            "google": "Google",
            "ollama": "Ollama (local)",
            "openrouter": "OpenRouter"
        }
        
        self.llm_models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
            "google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "ollama": ["llama3.2", "llama3.1", "qwen2.5"],
            "openrouter": ["openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022"]
        }
    
    async def setup(self) -> bool:
        """Set connection"""
        try:
            print("🔗 Connecting to TradingAgents...")
            agent_url = await self.connections.start_agent(self.agent_name)
            self.client = await self.connections.get_client(self.agent_name)
            print(f"✅ Connected successfully: {agent_url}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Please ensure TradingAgents adapter is running")
            return False
    
    def print_header(self):
        """Print program header"""
        print("\n" + "="*70)
        print("🚀 TradingAgents interactive analysis client")
        print("="*70)
        print("Supports multiple LLM providers, multiple analysts, and real-time stock analysis")
        print("Enter 'quit' to exit the program")
        print("="*70 + "\n")
    
    def select_ticker(self) -> Optional[str]:
        """Select stock code"""
        print("📈 Please select the stock to analyze:")
        print("-" * 40)
        
        tickers = list(self.available_tickers.keys())
        for i, (ticker, name) in enumerate(self.available_tickers.items(), 1):
            print(f"{i:2d}. {ticker:6s} - {name}")
        
        print(f"{len(tickers)+1:2d}. Custom input")
        
        while True:
            try:
                choice = input(f"\nPlease select (1-{len(tickers)+1}) or directly input stock code: ").strip()
                
                if not choice:
                    continue
                
                # Direct input stock code
                if choice.upper() in self.available_tickers:
                    return choice.upper()
                
                # Check if it's another valid stock code format
                if len(choice) <= 5 and choice.upper().isalpha():
                    confirm = input(f"Use stock code {choice.upper()}? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        return choice.upper()
                    continue
                
                # Number selection
                choice_num = int(choice)
                if 1 <= choice_num <= len(tickers):
                    return tickers[choice_num - 1]
                elif choice_num == len(tickers) + 1:
                    custom = input("Please input stock code: ").strip().upper()
                    if custom:
                        return custom
                else:
                    print("❌ Invalid choice, please try again")
                    
            except ValueError:
                print("❌ Please input valid number or stock code")
            except KeyboardInterrupt:
                return None
    
    def select_analysts(self) -> List[str]:
        """Select analysts"""
        print("\n👥 Please select analysts (can select multiple):")
        print("-" * 40)
        
        for i, analyst in enumerate(self.available_analysts, 1):
            print(f"{i}. {analyst:12s} - {self._get_analyst_description(analyst)}")
        
        print(f"{len(self.available_analysts)+1}. Select all")
        
        while True:
            try:
                choice = input(f"\nPlease select (1-{len(self.available_analysts)+1}) or use comma to separate multiple choices: ").strip()
                
                if not choice:
                    continue
                
                # Select all
                if choice == str(len(self.available_analysts)+1):
                    return self.available_analysts.copy()
                
                # Parse multiple choices
                selected = []
                for part in choice.split(','):
                    part = part.strip()
                    if part.isdigit():
                        num = int(part)
                        if 1 <= num <= len(self.available_analysts):
                            analyst = self.available_analysts[num-1]
                            if analyst not in selected:
                                selected.append(analyst)
                    elif part in self.available_analysts:
                        if part not in selected:
                            selected.append(part)
                
                if selected:
                    return selected
                else:
                    print("❌ Invalid choice, please try again")
                    
            except ValueError:
                print("❌ Please input valid number")
            except KeyboardInterrupt:
                return self.available_analysts.copy()
    
    def _get_analyst_description(self, analyst: str) -> str:
        """Get analyst description"""
        descriptions = {
            "market": "Market technical analysis",
            "social": "Social media sentiment",
            "news": "News event analysis", 
            "fundamentals": "Fundamental analysis"
        }
        return descriptions.get(analyst, "Unknown analyst")
    
    def select_llm_provider(self) -> Optional[str]:
        """Select LLM provider"""
        print("\n🤖 Please select LLM provider:")
        print("-" * 40)
        
        providers = list(self.llm_providers.keys())
        for i, (key, name) in enumerate(self.llm_providers.items(), 1):
            print(f"{i}. {name}")
        
        print(f"{len(providers)+1}. Use default (OpenAI)")
        
        while True:
            try:
                choice = input(f"\nPlease select (1-{len(providers)+1}): ").strip()
                
                if not choice or choice == str(len(providers)+1):
                    return None  # Use default
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(providers):
                    return providers[choice_num - 1]
                else:
                    print("❌ Invalid choice, please try again")
                    
            except ValueError:
                print("❌ Please input valid number")
            except KeyboardInterrupt:
                return None
    
    def select_models(self, provider: str) -> tuple[Optional[str], Optional[str]]:
        """Select model"""
        if provider not in self.llm_models:
            return None, None
        
        models = self.llm_models[provider]
        print(f"\n🔧 Please select model for {self.llm_providers[provider]}:")
        print("-" * 40)
        
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
        
        print(f"{len(models)+1}. Use default model")
        
        try:
            choice = input(f"\nPlease select deep thinking model (1-{len(models)+1}): ").strip()
            
            deep_model = None
            if choice and choice != str(len(models)+1):
                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    deep_model = models[choice_num - 1]
            
            choice = input(f"Please select quick thinking model (1-{len(models)+1}): ").strip()
            
            quick_model = None
            if choice and choice != str(len(models)+1):
                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    quick_model = models[choice_num - 1]
            
            return deep_model, quick_model
            
        except (ValueError, KeyboardInterrupt):
            return None, None
    
    def get_analysis_date(self) -> Optional[str]:
        """Get analysis date"""
        print("\n📅 Please input analysis date:")
        print("-" * 40)
        print("Format: YYYY-MM-DD (e.g.: 2024-01-15)")
        print("Directly press Enter to use today's date")
        
        try:
            date = input("\nAnalysis date: ").strip()
            return date if date else None
        except KeyboardInterrupt:
            return None
    
    def get_debug_mode(self) -> bool:
        """Get debug mode setting"""
        try:
            choice = input("\n🔍 Whether to enable debug mode? (y/n): ").strip().lower()
            return choice in ['y', 'yes']
        except KeyboardInterrupt:
            return False
    
    def build_query(self, ticker: str, analysts: List[str], provider: Optional[str], 
                   deep_model: Optional[str], quick_model: Optional[str], 
                   date: Optional[str], debug: bool) -> str:
        """Build query string"""
        query_parts = [f"Analyze {ticker} stock"]
        
        if analysts and len(analysts) < len(self.available_analysts):
            analyst_names = [f"{a}" for a in analysts]
            query_parts.append(f"Use {','.join(analyst_names)} analysts")
        
        if provider:
            query_parts.append(f"Use {provider} provider")
        
        if deep_model:
            query_parts.append(f"Deep model {deep_model}")
        
        if quick_model:
            query_parts.append(f"Quick model {quick_model}")
        
        if date:
            query_parts.append(f"Date {date}")
        
        if debug:
            query_parts.append("Enable debug mode")
        
        return "，".join(query_parts)
    
    async def run_analysis(self, query: str):
        """Run analysis"""
        print(f"\n🎯 Execute analysis: {query}")
        print("="*70)
        
        try:
            async for task, event in await self.client.send_message(
                query,
                streaming=True,
            ):
                if event and hasattr(event, 'content'):
                    print(event.content, end='', flush=True)
            
            print("\n" + "="*70)
            
        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
    
    async def interactive_mode(self):
        """Interactive mode"""
        while True:
            try:
                print("\n" + "🔄 Start new analysis")
                print("-" * 30)
                
                # Select stock
                ticker = self.select_ticker()
                if not ticker:
                    break
                
                # Select analysts
                analysts = self.select_analysts()
                
                # Select LLM provider
                provider = self.select_llm_provider()
                
                # Select model
                deep_model, quick_model = None, None
                if provider:
                    deep_model, quick_model = self.select_models(provider)
                
                # Select date
                date = self.get_analysis_date()
                
                # Debug mode
                debug = self.get_debug_mode()
                
                # Build and execute query
                query = self.build_query(ticker, analysts, provider, deep_model, quick_model, date, debug)
                await self.run_analysis(query)
                
                # Ask if continue
                continue_choice = input("\n🔄 Whether to continue analyzing other stocks? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 User interrupted")
                break
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.connections.stop_all()
        except Exception as e:
            logger.error(f"Cleanup resources failed: {e}")


async def main():
    """Main function"""
    client = TradingAgentsInteractiveClient()
    
    try:
        client.print_header()
        
        if not await client.setup():
            return
        
        await client.interactive_mode()
        
    except KeyboardInterrupt:
        print("\n👋 Program interrupted")
    finally:
        await client.cleanup()
        print("👋 Bye!")


if __name__ == "__main__":
    asyncio.run(main())
