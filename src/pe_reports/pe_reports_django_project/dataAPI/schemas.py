"""Pydantic models used by FastAPI"""
from pydantic import BaseModel, Field, EmailStr, validator
from pydantic.types import UUID1
from typing import Optional, Any
from uuid import UUID, uuid4
from datetime import date, datetime

'''
Developer Note: If there comes an instance as in class Cidrs where there are
foreign keys. The data type will not be what is stated in the database. What is
happening is the data base is making a query back to the foreign key table and
returning it as the column in its entirety i.e. select * from <table>, so it 
will error and not be able to report on its data type. In these scenario's use
the data type "Any" to see what the return is.
'''

class OrganizationBase(BaseModel):
    name: str
    cyhy_db_name: str = None

class Organization(OrganizationBase):
    pass

    class Config:
        orm_mode = True

class VwBreachcomp(BaseModel):
    credential_exposures_uid: str
    email: str
    breach_name: str
    organizations_uid: str
    root_domain: str
    sub_domain: str
    hash_type: str
    name: str
    login_id: str
    password: str
    phone: str
    data_source_uid: str
    description: str
    breach_date: str
    added_date: str
    modified_date: str
    data_classes: str
    password_included: str
    is_verified: str
    is_fabricated: str
    is_sensitive: str
    is_retired: str
    is_spam_list: str


class VwBreachDetails(BaseModel):
    organizations_uid: str
    breach_name: str
    mod_date: str
    description: str
    breach_date: str
    password_included: str
    number_of_creds: str


class VwBreachcompCredsbydate(BaseModel):
    organizations_uid: str
    mod_date: str
    no_password: str
    password_included: str


class VwOrgsAttacksurface(BaseModel):
    organizations_uid: UUID
    cyhy_db_name: str
    num_ports: str
    num_root_domain: str
    num_sub_domain: str
    num_ips: str

    class Config:
        orm_mode = True


class VwOrgsAttacksurfaceInput(BaseModel):
    organizations_uid: UUID

    class Config:
        orm_mode = True


class CyhyDbAssets(BaseModel):
    # field_id: str
    org_id: str
    org_name: str
    contact: Optional[str] = None
    network: str
    type: str
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    currently_in_cyhy: Optional[str] = None

    class Config:
        orm_mode = True


class CyhyDbAssetsInput(BaseModel):
    org_id: str

    class Config:
        orm_mode = True


class Cidrs(BaseModel):
    cidr_uid: UUID
    network: str
    # organizations_uid: Any
    data_source_uid: Any
    insert_alert: Optional[str] = None


    class Config:
        orm_mode = True



class VwCidrs(BaseModel):
    cidr_uid: str
    network: str
    organizations_uid: str
    data_source_uid: str
    insert_alert: Optional[str] = None


class DataSource(BaseModel):

    data_source_uid: str
    name: str
    description: str
    last_run: str

    class Config:
        orm_mode = True



class UserAPIBase(BaseModel):
    # user_id: int
    refresh_token: str

class UserAPI(UserAPIBase):
    pass

    class Config():
        orm_mode = True




class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class UserAuth(BaseModel):
    # id: UUID = Field(..., description='user UUID')
    # email: EmailStr = Field(..., description="user email")
    username: str = Field(..., description="user name")
    # password: str = Field(..., min_length=5, max_length=24,
    #                       description="user password")

class UserOut(BaseModel):
    id: UUID
    email: str


class SystemUser(UserOut):
    password: str


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True


# Additional properties to return via API
class User(UserInDBBase):
    pass


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
