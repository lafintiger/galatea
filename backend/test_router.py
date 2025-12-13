"""Test the command router directly"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.command_router import command_router

async def test():
    print('Testing command router with Ministral...')
    print('=' * 50)
    
    tests = [
        'how many items on my todo list',
        'add get milk to my todo list', 
        'what is the weather',
        'tell me a joke',
        'remember to call mom',
        'get more cotton',
    ]
    
    for text in tests:
        print(f'\nInput: "{text}"')
        try:
            cmd, response = await command_router.route(text)
            if cmd:
                print(f'  TOOL DETECTED: {cmd.get("action")}')
                print(f'  Full command: {cmd}')
                print(f'  Response: {response}')
            else:
                print(f'  NO TOOL -> Goes to main LLM')
        except Exception as e:
            print(f'  ERROR: {type(e).__name__}: {e}')

if __name__ == '__main__':
    asyncio.run(test())

