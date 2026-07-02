
from sqlalchemy import inspect, create_engine, text, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, sessionmaker

from advcms.settings import app_settings


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id = Column('id', Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column('username', String, unique=True, nullable=False)
    password_hash = Column('password_hash', String, nullable=False)

class Post(Base):
    __tablename__ = 'posts'

    id = Column('id', Integer, primary_key=True, nullable=False, autoincrement=True)
    title = Column('title', String, nullable=False)
    slug = Column('slug', String, unique=True, nullable=False)
    category = Column('category', String)
    summary = Column('summary', String)
    content = Column('content', String, nullable=False)
    status = Column('status', String, nullable=False, default='draft')
    media_url = Column('media_url', String)
    created_at = Column('created_at', DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column('updated_at', DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    author_id = Column('author_id', Integer, ForeignKey('users.id'), nullable=False)

class DBConnection:
    
    def __init__(self):

        self.engine = None
        self.inspector = None
        self.session = None

    def __del__(self):

        if self.session:
            self.session.close()

        if self.engine:
            self.engine.dispose()

    def connect(self):

        try:
            self.engine = create_engine(app_settings.WEBSERVER_DB_URL)
            if self.engine is None:
                return -1

            self.inspector = inspect(self.engine)

            if self.inspector is None:
                return -2
                
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            if self.session is None:
                return -3
            
            self.session.execute(text('SELECT 1'))
            self.init_db()

            print('\n\n Database Connection successful !')
            return 1
        
        except Exception as e:
            print(f"Error initializing database: {e}")
            return -4

    def init_db(self):

        if self.engine is None:
            return -1

        if self.inspector is None:
            return -1
                
        non_existing_tables = list()

        if not self.inspector.has_table('users'):
            non_existing_tables.append(User.__table__)

        if not self.inspector.has_table('posts'):
            non_existing_tables.append(Post.__table__)

        if len(non_existing_tables) > 0:
            Base.metadata.create_all(self.engine, tables=non_existing_tables)

        if self.inspector.has_table('posts'):
            post_columns = {column['name'] for column in self.inspector.get_columns('posts')}
            if 'media_url' not in post_columns:
                with self.engine.begin() as connection:
                    connection.execute(text("ALTER TABLE posts ADD COLUMN media_url VARCHAR"))
        
        return len(non_existing_tables)

    def create_user(self, username: str, password_hash: str) -> int:
        
        if self.engine is None:
            return -1
                
        if self.session is None:
            return -2
        
        if not self.inspector.has_table('users'):
            return -3

        try:
            new_user = User(username=username, password_hash=password_hash)
            self.session.add(new_user)
            self.session.commit()
            return 1
        
        except Exception as e:
            self.session.rollback()
            print(f"Error creating user: {e}")
            return -4

    def get_user_by_username(self, username: str) -> Mapped[User] | None:

        if self.engine is None:
            return None
        
        if self.session is None:
            return None
        
        if not self.inspector.has_table('users'):
            return None

        try:
            user = self.session.query(User).filter(User.username == username).first()
            return user
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    def create_post(self, title: str, slug: str, category: str, summary: str, content: str, status: str, author_id: int, media_url: str | None = None) -> int:
   
        if self.engine is None:
            return -1
                
        if self.session is None:
            return -2
        
        if not self.inspector.has_table('posts'):
            return -3

        try:
            new_post = Post(title=title, slug=slug, category=category, summary=summary, content=content, status=status, media_url=media_url, author_id=author_id)
            self.session.add(new_post)
            self.session.commit()
            return 1
        
        except Exception as e:
            self.session.rollback()
            print(f"Error creating post: {e}")
            return -4

    def delete_post(self, post_id: int, author_id: int) -> int:
        
        if self.engine is None:
            return -1

        if self.session is None:
            return -2
        
        if not self.inspector.has_table('posts'):
            return -3

        try:
            post = self.session.query(Post).filter(Post.id == post_id, Post.author_id == author_id).first()
            if post:
                self.session.delete(post)
                self.session.commit()
                return 1
            return -4
        
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting post: {e}")
            return -5

    def get_post_by_id(self, post_id: int) -> Mapped[Post] | None:
        
        if self.engine is None:
            return None

        if self.session is None:
            return None

        try:
            post = self.session.query(Post).filter(Post.id == post_id).first()
            return post
        except Exception as e:
            print(f"Error fetching post: {e}")
            return None

    def get_post_by_slug(self, slug: str) -> Mapped[Post] | None:
        
        if self.engine is None:
            return None

        if self.session is None:
            return None

        try:
            post = self.session.query(Post).filter(Post.slug == slug).first()
            return post
        except Exception as e:
            print(f"Error fetching post: {e}")
            return None
    
    def get_all_published_posts(self) -> list[Mapped[Post]]:
        
        if self.engine is None:
            return []

        if self.session is None:
            return []

        try:
            posts = self.session.query(Post).filter(Post.status == "published").order_by(Post.created_at.desc()).all()
            return posts
        except Exception as e:
            print(f"Error fetching published posts: {e}")
            return []
           
    def get_posts_by_author(self, author_id: int) -> list[Mapped[Post]]:
        
        if self.engine is None:
            return []

        if self.session is None:
            return []

        try:
            posts = self.session.query(Post).filter(Post.author_id == author_id).order_by(Post.created_at.desc()).all()
            return posts
        except Exception as e:
            print(f"Error fetching posts by author: {e}")
            return []

    def update_post(self, post_id: int, title: str, slug: str, category: str, summary: str, content: str, status: str, author_id: int, media_url: str | None = None) -> int:
                
        if self.engine is None:
            return -1

        if self.session is None:
            return -2
        
        if not self.inspector.has_table('posts'):
            return -3

        try:
            posts = self.session.query(Post).filter(Post.id == post_id, Post.author_id == author_id)
            for post in posts:
                post.title = title
                post.slug = slug
                post.category = category
                post.summary = summary
                post.content = content
                post.status = status
                if media_url is not None:
                    post.media_url = media_url
            
            if posts.count() > 0:
                self.session.commit()

            return posts.count()
            
        except Exception as e:
            self.session.rollback()
            print(f"Error updating post: {e}")
            return -4
