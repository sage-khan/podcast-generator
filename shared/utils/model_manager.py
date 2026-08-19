import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ModelManager:
    """Manager for in-memory storage of trained models"""
    
    def __init__(self):
        """Initialize the model manager"""
        self.models = []
        self.next_id = 1
    
    def add_model(self, model_data: Dict[str, Any]) -> int:
        """
        Add a new model to the manager
        
        Args:
            model_data: Dictionary containing model data
            
        Returns:
            Model ID
        """
        # Generate a simple ID if not provided
        if 'id' not in model_data:
            model_data['id'] = self.next_id
            self.next_id += 1
        
        self.models.append(model_data)
        logger.debug(f"Added model with ID {model_data['id']}: {model_data['model_name']}")
        return model_data['id']
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a model by its ID
        
        Args:
            model_id: Model ID
            
        Returns:
            Model data or None if not found
        """
        try:
            model_id = int(model_id)
        except ValueError:
            return None
            
        for model in self.models:
            if model.get('id') == model_id:
                return model
        return None
    
    def get_model_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a model by its name
        
        Args:
            model_name: Model name
            
        Returns:
            Model data or None if not found
        """
        for model in self.models:
            if model.get('model_name') == model_name:
                return model
        return None
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        Get all models
        
        Returns:
            List of model data
        """
        return self.models
    
    def update_model(self, model_id: int, model_data: Dict[str, Any]) -> bool:
        """
        Update a model's data
        
        Args:
            model_id: Model ID
            model_data: Updated model data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            model_id = int(model_id)
        except ValueError:
            return False
            
        for i, model in enumerate(self.models):
            if model.get('id') == model_id:
                # Preserve the ID
                model_data['id'] = model_id
                self.models[i] = model_data
                return True
        return False
    
    def delete_model(self, model_id: int) -> bool:
        """
        Delete a model
        
        Args:
            model_id: Model ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            model_id = int(model_id)
        except ValueError:
            return False
            
        for i, model in enumerate(self.models):
            if model.get('id') == model_id:
                self.models.pop(i)
                return True
        return False
