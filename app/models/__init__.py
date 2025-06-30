from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class DatabaseObjectType(str, Enum):
    TABLE = "table"
    VIEW = "view"
    STORED_PROCEDURE = "stored_procedure"
    FUNCTION = "function"


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None


class ParameterInfo(BaseModel):
    name: str
    type: str
    direction: str = "IN"  # IN, OUT, INOUT
    default_value: Optional[str] = None
    nullable: bool = True


class IndexInfo(BaseModel):
    name: str
    columns: List[str]
    unique: bool = False
    clustered: bool = False


class RelationshipInfo(BaseModel):
    foreign_table: str
    foreign_column: str
    local_column: str
    relationship_type: str = "many_to_one"


class TableMetadata(BaseModel):
    name: str
    schema_name: str
    type: DatabaseObjectType
    columns: List[ColumnInfo]
    indexes: List[IndexInfo] = []
    relationships: List[RelationshipInfo] = []
    row_count: Optional[int] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None


class StoredProcedureMetadata(BaseModel):
    name: str
    schema_name: str
    type: DatabaseObjectType = DatabaseObjectType.STORED_PROCEDURE
    parameters: List[ParameterInfo] = []
    returns: List[ColumnInfo] = []
    related_tables: List[str] = []
    description: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None


class MetadataSuggestion(BaseModel):
    type: DatabaseObjectType
    name: str
    schema_name: str
    score: float
    params: List[ParameterInfo] = []
    returns: List[ColumnInfo] = []
    related_tables: List[str] = []
    description: Optional[str] = None


class SchemaOverview(BaseModel):
    schema_name: str
    table_count: int = 0
    procedure_count: int = 0
    function_count: int = 0
    tables: List[Dict[str, Any]] = []
    procedures: List[Dict[str, Any]] = []
    functions: List[Dict[str, Any]] = []


class DatabaseMetadataResponse(BaseModel):
    database_name: str
    database_type: str
    schemas: List[SchemaOverview]
    total_schemas: int
    total_tables: int
    total_procedures: int
    total_functions: int
    total_objects: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
