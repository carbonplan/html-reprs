from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager

import pydantic
from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

from .helpers import sanitize_url
from .log import get_logger

origins = ['*']

logger = get_logger()


@asynccontextmanager
async def lifespan_event(app: FastAPI):
    """
    Context manager that yields the application's startup and shutdown events.
    """
    logger.info('⏱️ Application startup...')

    worker_num = int(os.environ.get('APP_WORKER_ID', 9999))

    logger.info(f'👷 Worker num: {worker_num}')

    # set up cache
    logger.info('🔥 Setting up cache...')
    expiration = int(60 * 60 * 1)  # 24 hours
    cache_status_header = 'x-html-reprs-cache'
    FastAPICache.init(
        InMemoryBackend(),
        expire=expiration,
        cache_status_header=cache_status_header,
    )
    logger.info(
        f'🔥 Cache set up with expiration={expiration:,} seconds | {cache_status_header} cache status header.'
    )

    yield

    logger.info('Application shutdown...')
    logger.info('Clearing cache...')
    FastAPICache.reset()
    logger.info('👋 Goodbye!')


app = FastAPI(lifespan=lifespan_event)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/')
def index():
    return {'message': 'Hello World!'}


@app.get('/xarray/')
@cache(namespace='html-reprs')
async def xarray(
    url: pydantic.AnyUrl = Query(
        ...,
        description='URL to a zarr store',
        example='https://ncsa.osn.xsede.org/Pangeo/pangeo-forge/HadISST-feedstock/hadisst.zarr',
    ),
):
    logger.info(f'🚀 Starting to process request for URL: {url}')

    import time

    import xarray as xr
    import zarr

    start_time = time.time()

    error_message = f'❌ An error occurred while fetching the data from URL: {url}'
    # sanitize the URL
    logger.info('🧹 Sanitizing URL..')
    sanitized_url = sanitize_url(url.unicode_string())
    logger.info(f'🧹 Sanitized URL: {sanitized_url}')

    try:
        logger.info(f'📂 Attempting to open dataset from URL: {url}')
        ds = xr.open_dataset(sanitized_url, engine='zarr', chunks={})
        logger.info('✅ Successfully opened dataset. Generating HTML representation.')
        html = ds._repr_html_().strip()

        del ds
        logger.info('🧹 Cleaned up dataset object')

        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f'🏁 Request processed successfully in {processing_time:.2f} seconds')

        return {'html': html, 'url': url, 'sanitized_url': sanitized_url}

    except (zarr.errors.GroupNotFoundError, FileNotFoundError):
        message = traceback.format_exc()
        logger.error(f'🔍 {error_message}: Dataset not found\n{message}')
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'detail': f'{error_message} Dataset not found. 😕'},
        )

    except PermissionError:
        message = traceback.format_exc()
        logger.error(f'🔒 {error_message}: Permission denied\n{message}')
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={'detail': f'{error_message} Permission denied. 🚫'},
        )

    except Exception as e:
        message = traceback.format_exc()
        logger.error(f'💥 {error_message}: Unexpected error\n{message}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'detail': f'{error_message} {str(e)} 😱'},
        )
