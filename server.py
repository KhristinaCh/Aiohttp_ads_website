from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, func
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
import json
import bcrypt
from typing import Optional


app = web.Application()

PG_DSN = 'postgresql+asyncpg://app:1234@127.0.0.1:5431/ads_website_2'
engine = create_async_engine(PG_DSN)
Base = declarative_base()


class HttpError(web.HTTPException):

    def __init__(self, message, *args, **kwargs):
        response = json.dumps({
            'status': 'error',
            'message': message
        })

        super().__init__(*args, **kwargs, text=response, content_type='application/json')


class BadRequest(HttpError):
    status_code = 400


class NotFound(HttpError):
    status_code = 404


async def init_orm(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()
        async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        app.async_session_maker = async_session_maker
        yield


class CreateAdSchema(BaseModel):
    name: str
    description: str
    owner: str


class PatchAdSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    owner: Optional[str]


class Ad(Base):
    __tablename__ = 'ads'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    description = Column(String(1024), nullable=False)
    creation_time = Column(DateTime, server_default=func.now())
    owner = Column(String(64), nullable=False)


async def get_ad(session, ad_id):
    ad = await session.get(Ad, ad_id)
    if not ad:
        raise NotFound(message='ad does not exist')
    return ad


class AdView(web.View):

    async def get(self):
        ad_id = int(self.request.match_info['ad_id'])
        async with app.async_session_maker() as session:
            ad = await get_ad(session, ad_id)
            return web.json_response({
                'name': ad.name,
                'creation_time': int(ad.creation_time.timestamp()),
                'owner': ad.owner
            })

    async def post(self):
        ad_data = await self.request.json()
        try:
            ad_data_validate = CreateAdSchema(**ad_data).dict()
        except ValidationError as err:
            # response = web.json_response({'status': 'error',
            #                               'description': err.errors()},
            #                               status=400)
            # return response
            # raise web.HTTPBadRequest(text=json.dumps({'error': err.errors()}),
            #                          content_type='application/json')
            raise BadRequest(message=err.errors())
        ad_data_validate['owner'] = (bcrypt.hashpw(
            ad_data_validate['owner'].encode(),
            salt=bcrypt.gensalt())).decode()
        new_ad = Ad(**ad_data_validate)
        async with app.async_session_maker() as session:
            session.add(new_ad)
            await session.commit()
            return web.json_response({'status': 'ok', 'id': new_ad.id})

    async def patch(self):
        ad_id = int(self.request.match_info['ad_id'])
        ad_data = await self.request.json()
        try:
            ad_data_validate = PatchAdSchema(**ad_data).dict(exclude_none=True)
        except ValidationError as err:
            raise BadRequest(message=err.errors())
        async with app.async_session_maker() as session:
            ad = await get_ad(session, ad_id)
            for key, value in ad_data_validate.items():
                setattr(ad, key, value)
            await session.commit()
            return web.json_response({'status': 'ok', 'name': ad.name})

    async def delete(self):
        ad_id = int(self.request.match_info['ad_id'])
        async with app.async_session_maker() as session:
            ad = await get_ad(session, ad_id)
            await session.delete(ad)
            await session.commit()
            return web.json_response({'status': 'ok'})


app.add_routes([web.route('POST', '/ads', AdView),
                web.route('GET', '/ads/{ad_id:\d+}', AdView),
                web.route('PATCH', '/ads/{ad_id:\d+}', AdView),
                web.route('DELETE', '/ads/{ad_id:\d+}', AdView)])
app.cleanup_ctx.append(init_orm)
web.run_app(app)
