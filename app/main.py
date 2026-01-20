from fastapi import FastAPI, HTTPException
from lifespan import lifespan
from dependency import SessionDependency
from schemes import CreateAdvertisementRequest, SearchAdvResponse, UpdateAdvertisement, \
    GetAdvertisement
import models, crud
from sqlalchemy import select, func, or_, and_
from typing import Optional


app = FastAPI(
    title='REST API',
    lifespan=lifespan
)


@app.post('/advertisements', status_code=201)
async def create_advertisement(adv: CreateAdvertisementRequest, session: SessionDependency):
    adv_dict = adv.model_dump(exclude_unset=True)
    adv_orm_obj = models.Advertisement(**adv_dict)
    await crud.add_item(session, adv_orm_obj)
    return adv_orm_obj.dict


@app.get('/advertisements/{adv_id}')
async def get_advertisement(adv_id: int, session: SessionDependency):
    adv_orm_obj = await crud.get_item_by_id(session, models.Advertisement, adv_id)
    return adv_orm_obj


@app.get('/advertisements', response_model=SearchAdvResponse)
async def search_advertisement(
        session: SessionDependency,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        search_mode: str = 'AND',
        limit: int = 100,
        offset: int = 0
):

    if price_min is not None and price_max is not None:
        if price_min > price_max:
            raise HTTPException(status_code=404, detail='Минимальная цена не должна превышать максимальную')

    query = select(models.Advertisement)
    count_query = select(func.count()).select_from(models.Advertisement)

    if title or description or price_min is not None or price_max is not None:
        conditions = []

        if title:
            conditions.append(models.Advertisement.title.ilike(f'%{title}%'))

        if description:
            conditions.append(models.Advertisement.description.ilike(f'%{description}%'))

        if price_min:
            conditions.append(models.Advertisement.price >= price_min)

        if price_max:
            conditions.append(models.Advertisement.price <= price_max)

        if conditions:
            if search_mode.upper() == 'OR':
                condition = or_(*conditions)

            else:
                condition = and_(*conditions)

            query = query.where(condition)
            count_query = count_query.where(condition)

    query = query.order_by(models.Advertisement.date.desc())
    query = query.offset(offset).limit(limit)

    advs = await session.scalars(query)
    advs_list = list(advs)
    current_count = len(advs_list)
    total = await session.scalar(count_query)
    return {
        'results': [adv.dict for adv in advs_list],
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + current_count < total)
        }
    }



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


@app.delete('/advertisements/{adv_id}', status_code=204)
async def delete_advertisement(adv_id: int, session: SessionDependency):
    adv_orm_obj = await crud.get_item_by_id(session, models.Advertisement, adv_id)
    if not adv_orm_obj:
        raise HTTPException(status_code=404, detail='Объявление не найдено')
    await crud.delete_item(session, adv_orm_obj)