from abc import ABC, abstractmethod
from pathlib import Path

from nest.common.templates.base_template import BaseTemplate, get_module_strings
from nest.common.templates import Database


class ORMTemplate(BaseTemplate, ABC):
    def __init__(self, module_name: str, db_type: Database):
        super().__init__(
            module_name=module_name,
        )
        self.db_type = db_type

    def app_file(self):
        return f"""from config import config
from nest.core.app import App

app = App(
    description="PyNest service",
    modules=[]
)


@app.on_event("startup")
def startup():
    config.create_all()
"""

    @abstractmethod
    def config_file(self):
        raise NotImplementedError

    @abstractmethod
    def requirements_file(self):
        raise NotImplementedError

    def docker_file(self):
        return ""

    def dockerignore_file(self):
        return """__pycache__
*.pyc
*.pyo
*.pyd
.DS_Store
.env
"""

    def gitignore_file(self):
        return """__pycache__
*.pyc
*.pyo
*.pyd
.DS_Store
.env
"""

    def module_file(self):
        return f"""from .{self.module_name}_service import {self.capitalized_module_name}Service
from .{self.module_name}_controller import {self.capitalized_module_name}Controller


class {self.capitalized_module_name}Module:

    def __init__(self):
        self.providers = [{self.capitalized_module_name}Service]
        self.controllers = [{self.capitalized_module_name}Controller]
"""

    def model_file(self):
        return f"""from pydantic import BaseModel


class {self.capitalized_module_name}(BaseModel):
    name: str

"""

    def entity_file(self):
        return f"""from config import config
from sqlalchemy import Column, Integer, String, Float
    
    
class {self.capitalized_module_name}(config.Base):
    __tablename__ = "{self.module_name}"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)

"""

    def service_file(self):
        return f"""from .{self.module_name}_model import {self.capitalized_module_name}
from .{self.module_name}_entity import {self.capitalized_module_name} as {self.capitalized_module_name}Entity
from config import config
from nest.core.decorators import db_request_handler
from functools import lru_cache


@lru_cache()
class {self.capitalized_module_name}Service:

    def __init__(self):
        self.config = config
        self.session = self.config.get_db()
    
    @db_request_handler
    def add_{self.module_name}(self, {self.module_name}: {self.capitalized_module_name}):
        new_{self.module_name} = {self.capitalized_module_name}Entity(
            **{self.module_name}.dict()
        )
        self.session.add(new_{self.module_name})
        self.session.commit()
        return new_{self.module_name}.id

    @db_request_handler
    def get_{self.module_name}(self):
        return self.session.query({self.capitalized_module_name}Entity).all()

"""

    def controller_file(self):
        return f"""from nest.core import Controller, Get, Post, Depends

from .{self.module_name}_service import {self.capitalized_module_name}Service
from .{self.module_name}_model import {self.capitalized_module_name}


@Controller("{self.module_name}")
class {self.capitalized_module_name}Controller:

    service: {self.capitalized_module_name}Service = Depends({self.capitalized_module_name}Service)
    
    @Get("/")
    def get_{self.module_name}(self):
        return self.service.get_{self.module_name}()
                
    @Post("/")
    def add_{self.module_name}(self, {self.module_name}: {self.capitalized_module_name}):
        return self.service.add_{self.module_name}({self.module_name})
 """

    def settings_file(self):
        return f"""# This file is used to configure the nest server.
config:
    db_type: {self.db_type.value}
    is_async: false
"""

    @staticmethod
    def validate_config_file(src_path: Path) -> Path:
        config_file = src_path.parent / "config.py"
        if not config_file.exists():
            raise Exception("orm_config.py file not found")
        return config_file

    def create_module(self, module_name: str, src_path: Path):
        module_path = src_path / module_name
        self.create_folder(module_path)
        self.create_template(module_path / "__init__.py", "")
        self.create_template(
            module_path / f"{module_name}_module.py", self.module_file()
        )
        self.create_template(
            module_path / f"{module_name}_controller.py", self.controller_file()
        )
        self.create_template(
            module_path / f"{module_name}_service.py", self.service_file()
        )
        self.create_template(module_path / f"{module_name}_model.py", self.model_file())
        self.create_template(
            module_path / f"{module_name}_entity.py", self.entity_file()
        )
        self.append_module_to_app(src_path.parent / "app.py")

    def generate_module(self, module_name: str):
        src_path = self.validate_new_module(module_name)
        self.validate_config_file(src_path)
        self.create_module(module_name, src_path)

    def generate_project(self, project_name: str):
        self.create_template(self.nest_path / "settings.yaml", self.settings_file())
        # define paths: root, src, module
        root_path = self.base_path / project_name
        src_path = self.base_path / project_name / "src"

        # create folders
        self.create_folder(root_path)
        self.create_folder(src_path)

        # create root level files
        self.create_template(root_path / "main.py", self.main_file())
        self.create_template(root_path / "README.md", self.readme_file())
        self.create_template(root_path / "app.py", self.app_file())
        self.create_template(root_path / "config.py", self.config_file())
        self.create_template(root_path / "requirements.txt", self.requirements_file())
        self.create_template(root_path / ".gitignore", self.gitignore_file())

        # create src level files
        self.create_template(src_path / "__init__.py", "")


class AsyncORMTemplate(ORMTemplate, ABC):
    def app_file(self):
        return f"""from config import config
from nest.core.app import App

app = App(
    description="PyNest service",
    modules=[]
)


@app.on_event("startup")
async def startup():
    await config.create_all()
"""

    @abstractmethod
    def config_file(self):
        pass

    @abstractmethod
    def requirements_file(self):
        pass


    def entity_file(self):
        return f"""from config import config
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class {self.capitalized_module_name}(config.Base):
    __tablename__ = "{self.module_name}"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)

"""

    def service_file(self):
        return f"""from .{self.module_name}_model import {self.capitalized_module_name}
from .{self.module_name}_entity import {self.capitalized_module_name} as {self.capitalized_module_name}Entity
from nest.core.decorators import async_db_request_handler

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class {self.capitalized_module_name}Service:

    @async_db_request_handler
    async def add_{self.module_name}(self, {self.module_name}: {self.capitalized_module_name}, session: AsyncSession):
        new_{self.module_name} = {self.capitalized_module_name}Entity(
            **{self.module_name}.dict()
        )
        session.add(new_{self.module_name})
        await session.commit()
        return new_{self.module_name}.id

    @async_db_request_handler
    async def get_{self.module_name}(self, session: AsyncSession):
        query = select({self.capitalized_module_name}Entity)
        result = await session.execute(query)
        return result.scalars().all()
"""

    def controller_file(self):
        return f"""from nest.core import Controller, Get, Post, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config import config


from .{self.module_name}_service import {self.capitalized_module_name}Service
from .{self.module_name}_model import {self.capitalized_module_name}


@Controller("{self.module_name}")
class {self.capitalized_module_name}Controller:

    service: {self.capitalized_module_name}Service = Depends({self.capitalized_module_name}Service)

    @Get("/")
    async def get_{self.module_name}(self, session: AsyncSession = Depends(config.get_db)):
        return await self.service.get_{self.module_name}(session)

    @Post("/")
    async def add_{self.module_name}(self, {self.module_name}: {self.capitalized_module_name}, session: AsyncSession = Depends(config.get_db)):
        return await self.service.add_{self.module_name}({self.module_name}, session)
 """

    def settings_file(self):
        return f"""# This file is used to configure the nest server.
config:
    db_type: {self.db_type.value}
    is_async: true
"""
