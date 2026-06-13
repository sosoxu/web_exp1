from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="draft")  # draft/configured/completed
    total_combinations = Column(Integer, default=0)
    filtered_combinations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    modules = relationship("ExperimentModule", back_populates="experiment", cascade="all, delete-orphan")
    params = relationship("ExperimentParam", back_populates="experiment", cascade="all, delete-orphan")
    constraints = relationship("ExperimentConstraint", back_populates="experiment", cascade="all, delete-orphan")
    combinations = relationship("ParamCombination", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentModule(Base):
    __tablename__ = "experiment_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    module_name = Column(String(200), nullable=False)
    module_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="modules")


class ExperimentParam(Base):
    __tablename__ = "experiment_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    module_name = Column(String(200), nullable=False)
    param_name = Column(String(200), nullable=False)
    param_id = Column(Integer, nullable=False)
    type_val = Column(String(20), nullable=False)
    vtype = Column(String(20), nullable=False)
    raw_description = Column(Text)
    parsed_values = Column(JSONB)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="params")


class ExperimentConstraint(Base):
    __tablename__ = "experiment_constraints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    constraint_type = Column(String(20), nullable=False)  # dependency/custom
    source_module = Column(String(200))
    source_param = Column(String(200))
    target_module = Column(String(200))
    target_param = Column(String(200))
    operator = Column(String(20))  # eq/neq/gt/lt/gte/lte/in/not_in
    constraint_value = Column(JSONB)
    raw_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="constraints")


class ParamCombination(Base):
    __tablename__ = "param_combinations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    combination_index = Column(Integer, nullable=False)
    combination_data = Column(JSONB, nullable=False)
    is_valid = Column(Boolean, default=True)
    invalid_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    experiment = relationship("Experiment", back_populates="combinations")
