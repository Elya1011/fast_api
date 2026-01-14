from fastapi import FastAPI, HTTPException
from lifespan import lifespan
from dependency import SessionDependency
from schemes import CreateAdvertisementRequest, SearchAdvResponse, AdvertisementFilter, UpdateAdvertisement, \
    GetAdvertisement, DeleteResponse
import models, crud
from sqlalchemy import select
from typing import Optional


app = FastAPI(
    title='REST API',
    lifespan=lifespan
)

@app.post('/advertisement')
async def create_advertisement(adv: CreateAdvertisementRequest, session: SessionDependency):
    adv_dict = adv.model_dump(exclude_unset=True)
    adv_orm_obj = models.Advertisement(**adv_dict)
    await crud.add_item(session, adv_orm_obj)
    return adv_orm_obj.dict


@app.get('/advertisement/{adv_id}')
async def search_advertisement(adv_id: int, session: SessionDependency):
    adv_orm_obj = await crud.get_item_by_id(session, models.Advertisement, adv_id)
    return adv_orm_obj


@app.get('/advertisement', response_model=SearchAdvResponse)
async def search_advertisement(
        session: SessionDependency,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None
):
    filters = AdvertisementFilter(
        title=title,
        description=description,
        price=price
    )

    if not filters.has_filters:
        query = select(models.Advertisement).limit(1000)

    else:
        query = select(models.Advertisement)

        if filters.title:
            query = query.where(models.Advertisement.title == filters.title)

        if filters.description:
            query = query.where(models.Advertisement.description == filters.description)

        if filters.price is not None:
            query = query.where(models.Advertisement.price == filters.price)

        query = query.limit(1000)

    advs = await session.scalars(query)
    return {'results': [adv.dict for adv in advs]}



@app.patch('/advertisements/{adv_id}', response_model=GetAdvertisement)
async def update_advertisement(adv_id: int, adv_data: UpdateAdvertisement, session: SessionDependency):
    query = select(models.Advertisement).where(models.Advertisement.id == adv_id)
    result = await session.scalars(query)
    adv = result.first()

    if not adv:
        raise HTTPException(status_code=404, detail='Объявление не найдено')

    update_data = adv_data.model_dump(exclude_unset=True)

    if not update_data:
        return {
            'id': adv.id,
            'title': adv.title,
            'description': adv.description,
            'price': float(adv.price) if adv.price else 0.0,
            'user': adv.user
        }

    for field, value in update_data.items():
        setattr(adv, field, value)

    try:
        await session.commit()
        await session.refresh(adv)

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f'Объявление при внесении изменений: {str(e)}')

    return {
            'id': adv.id,
            'title': adv.title,
            'description': adv.description,
            'price': float(adv.price) if adv.price else 0.0,
            'user': adv.user
    }


@app.delete('/advertisements/{adv_id}', response_model=DeleteResponse)
async def delete_advertisement(adv_id: int, session: SessionDependency):
    adv_orm_obj = await crud.get_item_by_id(session, models.Advertisement, adv_id)
    await crud.delete_item(session, adv_orm_obj)
    return {"status": "success"}