"""
Comprehensive test of the todo/workspace flow
Run this BEFORE telling user to test!
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.command_router import command_router

async def test_command_router():
    print('='*60)
    print('TEST 1: Command Router - Transcription Variations')
    print('='*60)
    
    tests = [
        'how many items in my taboo list',  # Whisper mis-heard "todo" as "taboo"
        'how many items in my todo list',
        'how many items on my to do list',
        'what is on my todo list',
        'read my todos',
        'show my task list',
    ]
    
    results = []
    for text in tests:
        try:
            cmd, resp = await command_router.route(text)
            action = cmd.get('action') if cmd else 'NO MATCH'
            results.append((text, action))
            status = '[OK]' if action == 'read_todos' else '[FAIL]'
            print(f'  {status} "{text}"')
            print(f'      -> {action}')
        except Exception as e:
            print(f'  [ERR] "{text}" -> ERROR: {e}')
            results.append((text, f'ERROR: {e}'))
    
    # Check if "taboo" variation works
    taboo_result = [r for r in results if 'taboo' in r[0]][0]
    if taboo_result[1] != 'read_todos':
        print()
        print('[WARN] PROBLEM: "taboo list" not recognized as "todo list"!')
        print('   Whisper often mis-transcribes "todo" as "taboo"')
        print('   Need to add this to the router system prompt')
        return False
    return True

async def test_add_todo():
    print()
    print('='*60)
    print('TEST 2: Command Router - Adding Todos')
    print('='*60)
    
    tests = [
        'add get milk to my todo list',
        'remember to call mom',
        'get more cotton',
        'add todo buy groceries',
    ]
    
    for text in tests:
        try:
            cmd, resp = await command_router.route(text)
            action = cmd.get('action') if cmd else 'NO MATCH'
            content = cmd.get('content', cmd.get('message', '')) if cmd else ''
            status = '[OK]' if action == 'add_todo' else ('[?]' if action == 'clarify' else '[FAIL]')
            print(f'  {status} "{text}"')
            print(f'      -> {action}: {content[:50]}...' if content else f'      -> {action}')
        except Exception as e:
            print(f'  [ERR] "{text}" -> ERROR: {e}')

async def main():
    print('GALATEA WORKSPACE FLOW TEST')
    print('Run this to verify changes before user testing!')
    print()
    
    router_ok = await test_command_router()
    await test_add_todo()
    
    print()
    print('='*60)
    if not router_ok:
        print('[FAILED] TESTS FAILED - Fix issues before user testing!')
    else:
        print('[PASSED] Basic routing works - but verify full flow manually')
    print('='*60)

if __name__ == '__main__':
    asyncio.run(main())

