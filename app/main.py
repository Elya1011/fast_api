from datetime import datetime
from security import check_password
from fastapi import FastAPI, HTTPException
from lifespan import lifespan
from dependency import SessionDependency, TokenDependency, CurrentUserDependency
from schemes import CreateAdvertisementRequest, SearchAdvResponse, UpdateAdvertisement, \
    GetAdvertisement, CreateUserRequest, LoginResponse, LoginRequest, UpdateUser
import models, crud
from sqlalchemy import select, func, or_, and_
from typing import Optional


app = FastAPI(
    title='REST API',
    lifespan=lifespan
)


@app.post('/user', tags=['user'], status_code=201)
async def create_user(user: CreateUserRequest, session: SessionDependency):
    query = select(models.User).where(models.User.email == user.email)
    result = await session.scalars(query)
    if result.first():
        raise HTTPException(status_code=400, detail='Пользователь с таким email уже существует')

    user_orm_obj = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email
    )
    await user_orm_obj.set_password(user.password)
    await crud.add_item(session, user_orm_obj)
    return user_orm_obj.dict


@app.post('/login', tags=['login'], status_code=200, response_model=LoginResponse)
async def login_user(login_data: LoginRequest, session: SessionDependency):
    query = select(models.User).where(models.User.email == login_data.email)
    user =await session.scalar(query)
    if user is None:
        raise HTTPException(401, 'Invalid credentials')
    if not await check_password(login_data.password, user.password_hash):
        raise HTTPException(401, 'Invalid credentials')
    token = models.Token(user_id=user.id)
    await crud.add_item(session, token)
    return token.dict


@app.patch('/user/{user_id}', tags=['user'], status_code=200)
async def edit_user(
        user_id: int,
        data: UpdateUser,
        session: SessionDependency,
        token: TokenDependency,
        current_user: CurrentUserDependency
):
    if current_user.id != user_id and not getattr(current_user, 'admin', False):
        raise HTTPException(status_code=403, detail="you don't have permission to edit this user")
    query = select(models.User).where(models.User.id == user_id)
    user_to_edit = await session.scalar(query)
    if not user_to_edit:
        raise HTTPException(status_code=404, detail=f'User with ID {user_id} not found')

    if data.email and data.email != user_to_edit.email:
        query = select(models.User).where(models.User.email == data.email, models.User.id != user_id)
        existing_user = await session.scalar(query)

        if existing_user:
            raise HTTPException(status_code=400, detail='email already registered')

    update_data = data.dict(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(user_to_edit, field, value)

        user_to_edit.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(user_to_edit)
    return user_to_edit.dict


@app.get('/user/{user_id}', tags=['user'], status_code=200)
async def get_user(user_id: int, session: SessionDependency):
    user_orm_obj = await crud.get_item_by_id(session, models.User, user_id)
    return user_orm_obj.dict


@app.delete('/user/{user_id}', tags=['user'], status_code=204)
async def delete_user(user_id: int, session: SessionDependency, token: TokenDependency, current_user: CurrentUserDependency):
    user_orm_obj = await crud.get_item_by_id(session, models.User, user_id)
    if not user_orm_obj:
        raise HTTPException(status_code=404, detail='user not found')
    if current_user.role != 'admin' and current_user.id != user_id:
        raise HTTPException(403, 'You can only delete your own account')
    await crud.delete_item(session, user_orm_obj)


@app.post('/advertisements', status_code=201)
async def create_advertisement(adv: CreateAdvertisementRequest, session: SessionDependency, token: TokenDependency):
    adv_dict = adv.model_dump(exclude_unset=True)
    adv_orm_obj = models.Advertisement(**adv_dict, user_id=token.user_id)
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



@app.patch('/advertisements/{adv_id}', response_model=GetAdvertisement) # add token
async def update_advertisement(adv_id: int, adv_data: UpdateAdvertisement, session: SessionDependency, token: TokenDependency):
    query = select(models.Advertisement).where(models.Advertisement.id == adv_id)
    result = await session.scalars(query)
    adv = result.first()

    if not adv:
        raise HTTPException(status_code=404, detail='Объявление не найдено')

    if token.user.role != 'admin' and token.user_id != adv.user_id:
        raise HTTPException(403, 'You can change only your own advertisements')

    update_data = adv_data.model_dump(exclude_unset=True)

    if not update_data:
        return {
            'id': adv.id,
            'title': adv.title,
            'description': adv.description,
            'price': float(adv.price) if adv.price else 0.0,
            'user': str(adv.user_id)
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
            'user': str(adv.user_id)
    }


@app.delete('/advertisements/{adv_id}', status_code=204)
async def delete_advertisement(adv_id: int, session: SessionDependency, token: TokenDependency):
    adv_orm_obj = await crud.get_item_by_id(session, models.Advertisement, adv_id)
    if not adv_orm_obj:
        raise HTTPException(status_code=404, detail='Объявление не найдено')
    if token.user.role != 'admin' and token.user_id != adv_orm_obj.user_id:
        raise HTTPException(403, 'You can only delete your own advertisements')
    await crud.delete_item(session, adv_orm_obj)