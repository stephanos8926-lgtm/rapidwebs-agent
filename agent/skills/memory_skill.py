"""Memory Skill - Persistent context storage (MCP-equivalent).

Provides entity-relation memory graph for long-term context persistence.
Similar to MCP memory server but optimized for Python/rw-agent.

Features:
- Create/read/update/delete entities
- Create/query relations between entities
- Search across entities and relations
- Automatic relevance scoring
- SQLite storage for persistence
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional



class MemorySkill:
    """Persistent memory and context storage."""

    def __init__(self, config: Any):
        self.config = config
        self.name = 'memory'
        self.enabled = True
        self.storage_path = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'memory.db'
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with schema."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.storage_path))
        cursor = conn.cursor()
        
        # Entities table - stores knowledge entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                UNIQUE(name, type)
            )
        ''')
        
        # Relations table - stores relationships between entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity_id INTEGER NOT NULL,
                target_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                UNIQUE(source_entity_id, target_entity_id, relation_type)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_entity_id)')
        
        conn.commit()
        conn.close()

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute memory operation."""
        actions = {
            'create_entity': self._create_entity,
            'get_entity': self._get_entity,
            'update_entity': self._update_entity,
            'delete_entity': self._delete_entity,
            'list_entities': self._list_entities,
            'create_relation': self._create_relation,
            'get_relations': self._get_relations,
            'delete_relation': self._delete_relation,
            'search': self._search,
            'query': self._query,
        }
        
        if action not in actions:
            return {
                'success': False,
                'error': f'Unknown action: {action}',
                'available_actions': list(actions.keys())
            }
        
        try:
            result = await actions[action](**kwargs)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.storage_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def _create_entity(self, name: str, type: str, content: str = "", 
                            metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new entity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO entities (name, type, content, metadata, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, type, content, json.dumps(metadata or {})))
            
            entity_id = cursor.lastrowid
            conn.commit()
            
            return {
                'success': True,
                'action': 'create_entity',
                'entity_id': entity_id,
                'name': name,
                'type': type
            }
        finally:
            conn.close()

    async def _get_entity(self, name: str, type: Optional[str] = None) -> Dict[str, Any]:
        """Get an entity by name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if type:
                cursor.execute('SELECT * FROM entities WHERE name = ? AND type = ?', (name, type))
            else:
                cursor.execute('SELECT * FROM entities WHERE name = ?', (name,))
            
            row = cursor.fetchone()
            
            if not row:
                return {
                    'success': False,
                    'error': f'Entity not found: {name}'
                }
            
            # Increment access count
            cursor.execute('''
                UPDATE entities SET access_count = access_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row['id'],))
            conn.commit()
            
            return {
                'success': True,
                'action': 'get_entity',
                'entity': {
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'content': row['content'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'access_count': row['access_count']
                }
            }
        finally:
            conn.close()

    async def _update_entity(self, name: str, type: str, content: Optional[str] = None,
                            metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Update an existing entity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current entity
            cursor.execute('SELECT * FROM entities WHERE name = ? AND type = ?', (name, type))
            row = cursor.fetchone()
            
            if not row:
                return {
                    'success': False,
                    'error': f'Entity not found: {name}'
                }
            
            # Update fields
            new_content = content if content is not None else row['content']
            new_metadata = metadata if metadata is not None else json.loads(row['metadata'])
            
            cursor.execute('''
                UPDATE entities 
                SET content = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ? AND type = ?
            ''', (new_content, json.dumps(new_metadata), name, type))
            
            conn.commit()
            
            return {
                'success': True,
                'action': 'update_entity',
                'name': name,
                'type': type
            }
        finally:
            conn.close()

    async def _delete_entity(self, name: str, type: str) -> Dict[str, Any]:
        """Delete an entity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM entities WHERE name = ? AND type = ?', (name, type))
            deleted = cursor.rowcount
            conn.commit()
            
            return {
                'success': True,
                'action': 'delete_entity',
                'deleted': deleted > 0
            }
        finally:
            conn.close()

    async def _list_entities(self, type: Optional[str] = None, 
                            limit: int = 50) -> Dict[str, Any]:
        """List entities, optionally filtered by type."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if type:
                cursor.execute('''
                    SELECT id, name, type, created_at, access_count 
                    FROM entities 
                    WHERE type = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                ''', (type, limit))
            else:
                cursor.execute('''
                    SELECT id, name, type, created_at, access_count 
                    FROM entities 
                    ORDER BY updated_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            
            return {
                'success': True,
                'action': 'list_entities',
                'entities': [
                    {
                        'id': row['id'],
                        'name': row['name'],
                        'type': row['type'],
                        'created_at': row['created_at'],
                        'access_count': row['access_count']
                    }
                    for row in rows
                ],
                'count': len(rows)
            }
        finally:
            conn.close()

    async def _create_relation(self, source: str, target: str, 
                              relation_type: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a relation between two entities."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get entity IDs
            cursor.execute('SELECT id FROM entities WHERE name = ?', (source,))
            source_row = cursor.fetchone()
            
            cursor.execute('SELECT id FROM entities WHERE name = ?', (target,))
            target_row = cursor.fetchone()
            
            if not source_row or not target_row:
                return {
                    'success': False,
                    'error': 'Source or target entity not found'
                }
            
            cursor.execute('''
                INSERT OR REPLACE INTO relations (source_entity_id, target_entity_id, relation_type, metadata)
                VALUES (?, ?, ?, ?)
            ''', (source_row['id'], target_row['id'], relation_type, json.dumps(metadata or {})))
            
            conn.commit()
            
            return {
                'success': True,
                'action': 'create_relation',
                'source': source,
                'target': target,
                'relation_type': relation_type
            }
        finally:
            conn.close()

    async def _get_relations(self, entity_name: str, 
                            direction: str = 'both') -> Dict[str, Any]:
        """Get relations for an entity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
            row = cursor.fetchone()
            
            if not row:
                return {
                    'success': False,
                    'error': f'Entity not found: {entity_name}'
                }
            
            entity_id = row['id']
            relations = []
            
            # Outgoing relations
            if direction in ['outgoing', 'both']:
                cursor.execute('''
                    SELECT r.relation_type, r.metadata, e.name as target_name, e.type as target_type
                    FROM relations r
                    JOIN entities e ON r.target_entity_id = e.id
                    WHERE r.source_entity_id = ?
                ''', (entity_id,))
                for rel_row in cursor.fetchall():
                    relations.append({
                        'direction': 'outgoing',
                        'relation_type': rel_row['relation_type'],
                        'target': rel_row['target_name'],
                        'target_type': rel_row['target_type'],
                        'metadata': json.loads(rel_row['metadata']) if rel_row['metadata'] else {}
                    })
            
            # Incoming relations
            if direction in ['incoming', 'both']:
                cursor.execute('''
                    SELECT r.relation_type, r.metadata, e.name as source_name, e.type as source_type
                    FROM relations r
                    JOIN entities e ON r.source_entity_id = e.id
                    WHERE r.target_entity_id = ?
                ''', (entity_id,))
                for rel_row in cursor.fetchall():
                    relations.append({
                        'direction': 'incoming',
                        'relation_type': rel_row['relation_type'],
                        'source': rel_row['source_name'],
                        'source_type': rel_row['source_type'],
                        'metadata': json.loads(rel_row['metadata']) if rel_row['metadata'] else {}
                    })
            
            return {
                'success': True,
                'action': 'get_relations',
                'entity': entity_name,
                'relations': relations,
                'count': len(relations)
            }
        finally:
            conn.close()

    async def _delete_relation(self, source: str, target: str, 
                              relation_type: str) -> Dict[str, Any]:
        """Delete a relation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id FROM entities WHERE name = ?', (source,))
            source_row = cursor.fetchone()
            
            cursor.execute('SELECT id FROM entities WHERE name = ?', (target,))
            target_row = cursor.fetchone()
            
            if not source_row or not target_row:
                return {
                    'success': False,
                    'error': 'Source or target entity not found'
                }
            
            cursor.execute('''
                DELETE FROM relations 
                WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?
            ''', (source_row['id'], target_row['id'], relation_type))
            
            deleted = cursor.rowcount
            conn.commit()
            
            return {
                'success': True,
                'action': 'delete_relation',
                'deleted': deleted > 0
            }
        finally:
            conn.close()

    async def _search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search entities by content."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Simple text search - could be enhanced with FTS5
            cursor.execute('''
                SELECT id, name, type, content, access_count,
                       (access_count * 0.1) as relevance
                FROM entities
                WHERE content LIKE ? OR name LIKE ?
                ORDER BY relevance DESC, updated_at DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'content': row['content'][:200] if row['content'] else '',
                    'access_count': row['access_count'],
                    'relevance': row['relevance']
                })
            
            return {
                'success': True,
                'action': 'search',
                'query': query,
                'results': results,
                'count': len(results)
            }
        finally:
            conn.close()

    async def _query(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """Advanced query operations."""
        
        if query_type == 'find_by_type':
            return await self._list_entities(type=kwargs.get('type'), limit=kwargs.get('limit', 50))
        
        elif query_type == 'find_connected':
            # Find all entities connected to a given entity
            entity_name = kwargs.get('entity')
            if not entity_name:
                return {'success': False, 'error': 'entity parameter required'}
            
            relations_result = await self._get_relations(entity_name, 'both')
            if not relations_result['success']:
                return relations_result
            
            # Get unique entity names from relations
            connected = set()
            for rel in relations_result['relations']:
                if rel['direction'] == 'outgoing':
                    connected.add(rel['target'])
                else:
                    connected.add(rel['source'])
            
            return {
                'success': True,
                'action': 'query',
                'query_type': 'find_connected',
                'entity': entity_name,
                'connected_entities': list(connected),
                'count': len(connected)
            }
        
        elif query_type == 'stats':
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT COUNT(*) as count, type FROM entities GROUP BY type')
                type_counts = {row['type']: row['count'] for row in cursor.fetchall()}
                
                cursor.execute('SELECT COUNT(*) as count FROM entities')
                total_entities = cursor.fetchone()['count']
                
                cursor.execute('SELECT COUNT(*) as count FROM relations')
                total_relations = cursor.fetchone()['count']
                
                return {
                    'success': True,
                    'action': 'query',
                    'query_type': 'stats',
                    'total_entities': total_entities,
                    'total_relations': total_relations,
                    'entities_by_type': type_counts
                }
            finally:
                conn.close()
        
        return {
            'success': False,
            'error': f'Unknown query type: {query_type}'
        }
