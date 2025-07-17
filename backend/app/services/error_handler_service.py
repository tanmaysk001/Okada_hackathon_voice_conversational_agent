"""
Comprehensive error handling and recovery system for the RAG chatbot.

This module provides:
1. Comprehensive error handling for all RAG operations
2. Automatic recovery mechanisms for common failures
3. User-friendly error messages with actionable guidance
4. System health monitoring and alerting
"""

import logging
import traceback
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better handling and recovery."""
    CHROMADB_CONNECTION = "chromadb_connection"
    INDEX_CREATION = "index_creation"
    RETRIEVER_CREATION = "retriever_creation"
    SEARCH_OPERATION = "search_operation"
    RESPONSE_GENERATION = "response_generation"
    USER_CONTEXT = "user_context"
    DOCUMENT_PROCESSING = "document_processing"
    SYSTEM_RESOURCE = "system_resource"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error tracking and debugging."""
    operation: str
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """Represents a recovery action that can be taken for an error."""
    name: str
    description: str
    action_func: Callable
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True


@dataclass
class ErrorRecord:
    """Record of an error occurrence with context and recovery attempts."""
    timestamp: datetime
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    stack_trace: str
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_actions: List[str] = field(default_factory=list)
    user_message: Optional[str] = None


class SystemHealthMonitor:
    """Monitors system health and tracks error patterns."""
    
    def __init__(self):
        self.error_history: List[ErrorRecord] = []
        self.health_metrics: Dict[str, Any] = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_success_rate": 0.0,
            "last_health_check": None,
            "system_status": "healthy"
        }
        self.alert_thresholds = {
            "critical_errors_per_hour": 5,
            "high_errors_per_hour": 20,
            "total_errors_per_hour": 100,
            "recovery_failure_rate": 0.5
        }
        
    def record_error(self, error_record: ErrorRecord):
        """Record an error and update health metrics."""
        self.error_history.append(error_record)
        self._update_health_metrics()
        self._check_alert_conditions(error_record)
    
    def _update_health_metrics(self):
        """Update system health metrics based on error history."""
        self.health_metrics["total_errors"] = len(self.error_history)
        self.health_metrics["errors_by_category"] = self._count_by_category(self.error_history)
        self.health_metrics["errors_by_severity"] = self._count_by_severity(self.error_history)
        self.health_metrics["recovery_success_rate"] = self._calculate_recovery_rate()
        
        # Determine system status based on recent errors
        recent_errors = [
            e for e in self.error_history 
            if e.timestamp > datetime.now() - timedelta(hours=1)
        ]
        self.health_metrics["last_health_check"] = datetime.now()
        self.health_metrics["system_status"] = self._determine_system_status(recent_errors)
    
    def _count_by_category(self, errors: List[ErrorRecord]):
        """Count errors by category."""
        categories = {}
        for error in errors:
            category = error.category.value
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        return categories
    
    def _count_by_severity(self, errors: List[ErrorRecord]):
        """Count errors by severity."""
        severities = {}
        for error in errors:
            severity = error.severity.value
            if severity in severities:
                severities[severity] += 1
            else:
                severities[severity] = 1
        return severities
    
    def _calculate_recovery_rate(self):
        """Calculate the success rate of recovery attempts."""
        recovery_attempts = [e for e in self.error_history if e.recovery_attempted]
        if not recovery_attempts:
            return 1.0  # No failures if no attempts
        
        successful_recoveries = [e for e in recovery_attempts if e.recovery_successful]
        return len(successful_recoveries) / len(recovery_attempts)
    
    def _determine_system_status(self, recent_errors: List[ErrorRecord]):
        """Determine overall system status based on recent errors."""
        if not recent_errors:
            return "healthy"
        
        # Count recent errors by severity
        critical = len([e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL])
        high = len([e for e in recent_errors if e.severity == ErrorSeverity.HIGH])
        total = len(recent_errors)
        
        # Apply thresholds
        if critical >= self.alert_thresholds["critical_errors_per_hour"]:
            return "critical"
        elif high >= self.alert_thresholds["high_errors_per_hour"]:
            return "degraded"
        elif total >= self.alert_thresholds["total_errors_per_hour"]:
            return "stressed"
        else:
            return "healthy"
            
    def _check_alert_conditions(self, error_record: ErrorRecord):
        """Check if alert conditions are met and log alerts."""
        # Log critical errors immediately
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                f"CRITICAL ERROR: {error_record.error_type} in {error_record.context.operation} - "
                f"{error_record.error_message}"
            )
        
        # Check system status after each update
        if self.health_metrics["system_status"] != "healthy":
            logger.warning(
                f"System status: {self.health_metrics['system_status']} - "
                f"Recent errors: {self.health_metrics['errors_by_category']}"
            )
    
    def get_health_report(self):
        """Get comprehensive health report."""
        self._update_health_metrics()
        
        # Calculate recent errors
        recent_errors = [
            e for e in self.error_history 
            if e.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        report = {
            "status": self.health_metrics["system_status"],
            "total_errors": self.health_metrics["total_errors"],
            "recent_errors_24h": len(recent_errors),
            "errors_by_category": self.health_metrics["errors_by_category"],
            "errors_by_severity": self.health_metrics["errors_by_severity"],
            "recovery_success_rate": self.health_metrics["recovery_success_rate"],
            "last_updated": self.health_metrics["last_health_check"],
        }
        
        return report


class RAGErrorHandler:
    """Main error handler for RAG operations with recovery mechanisms."""
    
    def __init__(self):
        self.health_monitor = SystemHealthMonitor()
        self.recovery_actions = self._initialize_recovery_actions()
        self.user_friendly_messages = self._initialize_user_messages()
    
    def _initialize_recovery_actions(self):
        """Initialize recovery actions for different error categories."""
        # In the simplified version, we'll return an empty dictionary
        # In a full implementation, this would contain recovery actions for various error categories
        return {}
    
    def _initialize_user_messages(self):
        """Initialize user-friendly error messages with actionable guidance."""
        return {
            ErrorCategory.UNKNOWN: {
                "default": "I encountered an unexpected error. Please try again or contact support if the issue persists."
            },
            ErrorCategory.CHROMADB_CONNECTION: {
                "default": "I'm having trouble connecting to the database. This might be a temporary issue."
            },
            ErrorCategory.INDEX_CREATION: {
                "default": "There was a problem processing your documents. Please try again later."
            },
            ErrorCategory.RETRIEVER_CREATION: {
                "default": "I'm having difficulty accessing your information. Please try again shortly."
            },
            ErrorCategory.SEARCH_OPERATION: {
                "default": "I couldn't complete your search request. Please try a different query or try again later."
            },
            ErrorCategory.RESPONSE_GENERATION: {
                "default": "I'm having trouble generating a response. Please try rephrasing your question."
            },
            ErrorCategory.USER_CONTEXT: {
                "default": "There was an issue with your user profile. Please try logging out and back in."
            },
            ErrorCategory.DOCUMENT_PROCESSING: {
                "default": "There was a problem processing one of your documents. The file might be corrupted or unsupported."
            },
            ErrorCategory.SYSTEM_RESOURCE: {
                "default": "The system is currently experiencing high load. Please try again in a few minutes."
            },
            ErrorCategory.EXTERNAL_API: {
                "default": "We're having trouble connecting to an external service. Please try again later."
            }
        }
    
    def handle_error(
            self,
            error: Exception,
            context: ErrorContext,
            category: Optional[ErrorCategory] = None,
            severity: Optional[ErrorSeverity] = None
        ):
        """
        Handle an error with automatic recovery attempts.
        
        Returns:
            (recovery_successful, user_message, recovered_result)
        """
        # Categorize and assess severity if not provided
        if not category:
            category = self._categorize_error(error, context)
        if not severity:
            severity = self._assess_severity(error, category, context)
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            category=category,
            severity=severity,
            context=context,
            stack_trace=traceback.format_exc()
        )
        
        # Log the error
        logger.error(
            f"Error in {context.operation}: {type(error).__name__}: {error} "
            f"[Category: {category.value}, Severity: {severity.value}]"
        )
        
        # Attempt recovery if possible
        recovery_successful = False
        recovered_result = None
        
        if category in self.recovery_actions:
            recovery_successful, recovered_result = self._attempt_recovery(
                error, context, category, error_record
            )
        
        # Update error record with recovery information
        error_record.recovery_attempted = category in self.recovery_actions
        error_record.recovery_successful = recovery_successful
        
        # Add user-friendly message
        error_record.user_message = self._get_user_message(
            category, severity, recovery_successful
        )
        
        # Record error in health monitor
        self.health_monitor.record_error(error_record)
        
        return recovery_successful, error_record.user_message, recovered_result
    
    def _categorize_error(self, error: Exception, context: ErrorContext):
        """Categorize error based on type and context."""
        # Simple categorization based on error type and operation
        error_type = type(error).__name__
        
        # In a full implementation, this would have more sophisticated logic
        # Default to UNKNOWN for simplified implementation
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, category: ErrorCategory, context: ErrorContext):
        """Assess error severity based on type, category, and context."""
        # Simple severity assessment
        # In a full implementation, this would have more sophisticated logic
        # Default to MEDIUM for simplified implementation
        return ErrorSeverity.MEDIUM
    
    def _attempt_recovery(
            self,
            error: Exception,
            context: ErrorContext,
            category: ErrorCategory,
            error_record: ErrorRecord
        ):
        """Attempt recovery using registered recovery actions."""
        if category not in self.recovery_actions:
            return False, None
        
        recovery_actions = self.recovery_actions[category]
        
        for action in recovery_actions:
            error_record.recovery_actions.append(action.name)
            
            # Try the recovery action
            try:
                result = action.action_func(error, context)
                return True, result
            except Exception as recovery_error:
                logger.warning(
                    f"Recovery action '{action.name}' failed: {recovery_error}"
                )
        
        return False, None
    
    def _get_user_message(self, category: ErrorCategory, severity: ErrorSeverity, recovery_successful: bool):
        """Get user-friendly error message."""
        if category in self.user_friendly_messages:
            if recovery_successful and "recovery_success" in self.user_friendly_messages[category]:
                return self.user_friendly_messages[category]["recovery_success"]
            
            severity_key = severity.value
            if severity_key in self.user_friendly_messages[category]:
                return self.user_friendly_messages[category][severity_key]
            
            return self.user_friendly_messages[category]["default"]
        
        return self.user_friendly_messages[ErrorCategory.UNKNOWN]["default"]
    
    def get_health_status(self):
        """Get current system health status."""
        return self.health_monitor.get_health_report()


# Global error handler instance
rag_error_handler = RAGErrorHandler()


@asynccontextmanager
async def error_handling_context(operation: str, user_id: Optional[str] = None, **kwargs):
    """Context manager for automatic error handling in RAG operations."""
    context = ErrorContext(
        operation=operation,
        user_id=user_id,
        details=kwargs
    )
    
    try:
        yield
    except Exception as e:
        # Handle the error
        recovery_successful, user_message, _ = rag_error_handler.handle_error(
            error=e,
            context=context
        )
        
        # Re-raise with user-friendly message for API endpoints to catch
        if not recovery_successful:
            raise type(e)(user_message) from e


def handle_sync_error(
    error: Exception,
    operation: str,
    user_id: Optional[str] = None,
    **kwargs
):
    """Synchronous error handler for non-async contexts."""
    context = ErrorContext(
        operation=operation,
        user_id=user_id,
        details=kwargs
    )
    
    # Handle the error
    recovery_successful, user_message, recovered_result = rag_error_handler.handle_error(
        error=error,
        context=context
    )
    
    return recovery_successful, user_message, recovered_result
