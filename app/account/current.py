from fastapi import HTTPException, Cookie, Request
from app.account.auth import decode_access_token


async def get_current_account(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    account_repo = request.app.state.account_repo
    account_id = payload.get("sub")
    account_id = payload.get("sub")
    if account_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    account = await account_repo.find_by_id(account_id)

    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    if account["is_blocked"]:
        raise HTTPException(status_code=401, detail="Account is blocked")

    return account
