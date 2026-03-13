from fastapi import HTTPException, Cookie
from app.account.auth import decode_access_token
from app.database.database import account_repo


async def get_current_account(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    account_id = int(payload.get("sub"))
    account = await account_repo.find_by_id(account_id)

    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    if account["is_blocked"]:
        raise HTTPException(status_code=401, detail="Account is blocked")

    return account
