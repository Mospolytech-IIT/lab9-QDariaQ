from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from typing import List
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, HTTPException, Request

#Часть 1: Подключение к базе данных и создание таблиц
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

class Base(DeclarativeBase): pass


class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)

class Post(Base):
    __tablename__ = "Posts"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)
    user_id = Column(Integer, ForeignKey(User.id))

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class PostCreate(BaseModel):
    title: str
    content: str
    user_id: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    user: UserResponse


#добавление пользователей
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate):
    db: Session = SessionLocal()
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return db_user

#добавление постов
@app.post("/posts/")
def create_post(post: PostCreate):
    db: Session = SessionLocal()
    db_post = Post(**post.dict())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    db.close()
    return {"id": db_post.id}

#извлечение всех пользователей
@app.get("/users/", response_model=List[UserResponse])
def get_users():
    db: Session = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users

#извлечение всех постов с информацией о пользователях
@app.get("/posts/", response_model=List[PostResponse])
def get_posts():
    db: Session = SessionLocal()
    posts = db.query(Post).all()
    result = []
    for post in posts:
        user = db.query(User).filter(User.id == post.user_id).first()
        result.append(PostResponse(id=post.id, title=post.title, content=post.content, user=UserResponse(id=user.id, username=user.username, email=user.email)))
    db.close()
    return result

#извлечение постов конкретного пользователя
@app.get("/users/{user_id}/posts/", response_model=List[PostResponse])
def get_user_posts(user_id: int):
    db: Session = SessionLocal()
    posts = db.query(Post).filter(Post.user_id == user_id).all()
    result = []
    for post in posts:
        user = db.query(User).filter(User.id == post.user_id).first()
        result.append(PostResponse(id=post.id, title=post.title, content=post.content, user=UserResponse(id=user.id, username=user.username, email=user.email)))
    db.close()
    return result

#обновление email пользователя
@app.put("/users/{user_id}/email/")
def update_user_email(user_id: int, email: str):
    db: Session = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    db_user.email = email
    db.commit()
    db.close()
    return {"message": "User email updated"}

#обновление контента поста
@app.put("/posts/{post_id}/content/")
def update_post_content(post_id: int, content: str):
    db: Session = SessionLocal()
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        db.close()
        raise HTTPException(status_code=404, detail="Post not found")
    db_post.content = content
    db.commit()
    db.close()
    return {"message": "Post content updated"}

#удаление поста
@app.delete("/posts/{post_id}/")
def delete_post(post_id: int):
    db: Session = SessionLocal()
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        db.close()
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    db.close()
    return {"message": "Post deleted"}

#удаление пользователя и всех его постов
@app.delete("/users/{user_id}/")
def delete_user(user_id: int):
    db: Session = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        db.close()
        raise HTTPException(status_code=404, detail="User not found")
    #удаление всех постов пользователя
    db.query(Post).filter(Post.user_id == user_id).delete()
    db.delete(db_user)
    db.commit()
    db.close()
    return {"message": "User and their posts deleted"}