from fastapi import APIRouter, Depends
from ..api_v1.endpoints.recaptcha import router as recaptcha_router
# from ..api_v1.endpoints.hello import hello_router
# from ..api_v1.key import validate_request


router = APIRouter()
router.include_router(recaptcha_router)

# router.include_router(hello_router,
#                       prefix="/hello",
#                       dependencies=[Depends(validate_request)]
#                       )
