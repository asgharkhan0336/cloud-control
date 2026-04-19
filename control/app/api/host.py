from fastapi import APIRouter, HTTPException, status

from app.services.libvirt_service import LibvirtService
from app.models.vm import HostInfoResponse, APIResponse

router = APIRouter(prefix="/api/v1", tags=["Host"])

@router.get("/host", response_model=HostInfoResponse)
async def get_host_info():
    """Get host system information"""
    try:
        with LibvirtService() as libvirt:
            host_info = libvirt.get_host_info()
            return HostInfoResponse(**host_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get host info: {str(e)}"
        )

@router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    try:
        with LibvirtService() as libvirt:
            libvirt.conn.getVersion()
            return APIResponse(
                success=True,
                message="Service is healthy",
                data={"libvirt": "connected"}
            )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Service unhealthy: {str(e)}"
        )
