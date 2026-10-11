import sys

from pymongo.errors import OperationFailure

from atlas import APP_DB, VAULT_DB, client_for

UNAUTHORIZED = 13


def main() -> int:
    ok = True

    agent = client_for("HARNESS_AGENT")
    try:
        agent[VAULT_DB].answers.find_one()
        print(f"FAIL harness_agent -> {VAULT_DB}: read succeeded")
        ok = False
    except OperationFailure as e:
        if e.code == UNAUTHORIZED:
            print(f"PASS harness_agent -> {VAULT_DB}: unauthorized (code {e.code})")
        else:
            print(f"FAIL harness_agent -> {VAULT_DB}: unexpected error code {e.code}: {e}")
            ok = False

    members = agent[APP_DB].members.count_documents({})
    print(f"{'PASS' if members == 3 else 'FAIL'} harness_agent -> {APP_DB}.members: {members} members")
    ok &= members == 3

    vault_reports = client_for("EVAL_RUNNER")[VAULT_DB].answers.count_documents({})
    print(f"{'PASS' if vault_reports == 22 else 'FAIL'} eval_runner -> {VAULT_DB}.answers: {vault_reports} reports")
    ok &= vault_reports == 22

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
