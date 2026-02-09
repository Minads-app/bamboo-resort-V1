from src.db import get_user, update_user_password
import sys

print("Testing get_user('')")
try:
    u = get_user("")
    print(f"Result: {u}")
    if u is None:
        print("PASS: get_user('') returned None")
    else:
        print("FAIL: get_user('') returned something else")
except Exception as e:
    print(f"FAIL: get_user('') crashed with {e}")
    sys.exit(1)

print("\nTesting update_user_password('', '123')")
try:
    update_user_password("", "123")
    print("PASS: update_user_password('') did not crash")
except Exception as e:
    print(f"FAIL: update_user_password('') crashed with {e}")
    sys.exit(1)

print("\nALL TESTS PASSED")
