from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.models.file import Base, File

engine = None
db_session = None

def init_db(app):
    """Initialize the database connection"""
    global engine, db_session
    
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    
    # Import all models here
    Base.query = db_session.query_property()
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove() 