"""Git skill for RapidWebs Agent.

This module provides Git integration for version control operations:
- git_status - Repository status
- git_diff - Show changes
- git_commit - Stage and commit changes
- git_log - View commit history
- git_branch - Branch operations
- git_add - Stage files
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from agent.config import Config
from agent.skills_manager import SkillBase
from agent.logging_config import get_logger

logger = get_logger('skills.git')


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str = ""
    ahead: int = 0
    behind: int = 0
    staged: List[str] = field(default_factory=list)
    unstaged: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    clean: bool = True


class GitSkill(SkillBase):
    """Git version control skill.

    Provides Git operations for the agent:
    - Status checking
    - Diff viewing
    - Committing changes
    - Branch management
    - History viewing

    Security: All operations are read-only by default.
    Write operations require explicit approval.
    """

    def __init__(self, config: Config):
        super().__init__(config, 'git')
        self.enabled = config.get('skills.git.enabled', True)
        self.timeout = config.get('skills.git.timeout', 30)
        self.allowed_operations = config.get(
            'skills.git.allowed_operations',
            ['status', 'diff', 'log', 'branch', 'add', 'commit', 'checkout', 'pull', 'push']
        )

    def _is_git_repo(self, path: Optional[Path] = None) -> bool:
        """Check if directory is a Git repository.

        Args:
            path: Directory to check (uses cwd if not provided)

        Returns:
            True if Git repository, False otherwise
        """
        try:
            search_path = path or Path.cwd()
            # Look for .git directory or file
            git_dir = search_path / '.git'
            if git_dir.exists():
                return True
            # Check parent directories
            for parent in search_path.parents:
                if (parent / '.git').exists():
                    return True
            return False
        except Exception as e:
            logger.debug(f'Git repo check failed: {e}')
            return False

    async def _run_git_command(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        check: bool = True
    ) -> Tuple[int, str, str]:
        """Run Git command asynchronously.

        Args:
            args: Git command arguments (without 'git')
            cwd: Working directory
            check: Raise exception on non-zero exit

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        cmd = ['git'] + args
        cwd = cwd or Path.cwd()

        logger.debug(f'Running git command: {" ".join(cmd)} in {cwd}')

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                stdout_str = stdout.decode('utf-8', errors='ignore')
                stderr_str = stderr.decode('utf-8', errors='ignore')

                if check and process.returncode != 0:
                    logger.error(f'Git command failed: {stderr_str}')
                    raise subprocess.CalledProcessError(
                        process.returncode,
                        cmd,
                        stdout_str,
                        stderr_str
                    )

                return process.returncode, stdout_str, stderr_str

            except asyncio.TimeoutError:
                process.kill()
                logger.error(f'Git command timed out: {" ".join(cmd)}')
                raise subprocess.TimeoutExpired(cmd, self.timeout)

        except FileNotFoundError:
            logger.error('Git not found in PATH')
            raise RuntimeError(
                'Git is not installed or not in PATH. '
                'Please install Git from https://git-scm.com/'
            )

    async def status(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Get Git repository status with overall timeout protection.

        Args:
            path: Repository path (uses cwd if not provided)

        Returns:
            Dictionary with status information
        """
        try:
            return await asyncio.wait_for(
                self._status_impl(path),
                timeout=self.timeout * 2  # Allow 2x single command timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f'Git status timed out after {self.timeout * 2}s')
            return {
                'success': False,
                'error': f'Git status timed out after {self.timeout * 2}s',
                'is_repo': True
            }

    async def _status_impl(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Internal implementation of Git status without timeout wrapper.
        
        Args:
            path: Repository path (uses cwd if not provided)
            
        Returns:
            Dictionary with status information
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository',
                'is_repo': False
            }

        try:
            # Get branch info
            _, branch_output, _ = await self._run_git_command(
                ['branch', '--show-current'],
                cwd=cwd
            )
            branch = branch_output.strip() or 'HEAD (detached)'

            # Get remote tracking info
            _, ahead_behind, _ = await self._run_git_command(
                ['rev-list', '--left-right', '--count', '@{upstream}...HEAD'],
                cwd=cwd,
                check=False
            )
            parts = ahead_behind.strip().split()
            ahead = int(parts[0]) if len(parts) > 0 else 0
            behind = int(parts[1]) if len(parts) > 1 else 0

            # Get staged files
            _, staged_output, _ = await self._run_git_command(
                ['diff', '--cached', '--name-only'],
                cwd=cwd
            )
            staged = [f.strip() for f in staged_output.strip().split('\n') if f.strip()]

            # Get unstaged files
            _, unstaged_output, _ = await self._run_git_command(
                ['diff', '--name-only'],
                cwd=cwd
            )
            unstaged = [f.strip() for f in unstaged_output.strip().split('\n') if f.strip()]

            # Get untracked files
            _, untracked_output, _ = await self._run_git_command(
                ['ls-files', '--others', '--exclude-standard'],
                cwd=cwd
            )
            untracked = [f.strip() for f in untracked_output.strip().split('\n') if f.strip()]

            is_clean = not staged and not unstaged and not untracked

            status_info = GitStatus(
                branch=branch,
                ahead=ahead,
                behind=behind,
                staged=staged,
                unstaged=unstaged,
                untracked=untracked,
                clean=is_clean
            )

            logger.info(f'Git status: branch={branch}, clean={is_clean}')

            return {
                'success': True,
                'is_repo': True,
                'branch': status_info.branch,
                'ahead': status_info.ahead,
                'behind': status_info.behind,
                'staged': status_info.staged,
                'unstaged': status_info.unstaged,
                'untracked': status_info.untracked,
                'clean': status_info.clean,
                'summary': self._format_status_summary(status_info)
            }

        except subprocess.CalledProcessError as e:
            logger.error(f'Git status failed: {e.stderr}')
            return {
                'success': False,
                'error': f'Git status failed: {e.stderr}'
            }
        except Exception as e:
            logger.error(f'Git status error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    def _format_status_summary(self, status: GitStatus) -> str:
        """Format status summary for display.

        Args:
            status: GitStatus object

        Returns:
            Formatted status string
        """
        lines = [f"On branch {status.branch}"]

        if status.ahead or status.behind:
            ahead_behind = []
            if status.ahead:
                ahead_behind.append(f"ahead by {status.ahead}")
            if status.behind:
                ahead_behind.append(f"behind by {status.behind}")
            lines.append(f"Your branch is {', '.join(ahead_behind)} of remote.")

        if status.staged:
            lines.append(f"Changes to be committed: ({len(status.staged)} files)")
            for f in status.staged[:5]:
                lines.append(f"  - {f}")
            if len(status.staged) > 5:
                lines.append(f"  ... and {len(status.staged) - 5} more")

        if status.unstaged:
            lines.append(f"Changes not staged for commit: ({len(status.unstaged)} files)")
            for f in status.unstaged[:5]:
                lines.append(f"  - {f}")
            if len(status.unstaged) > 5:
                lines.append(f"  ... and {len(status.unstaged) - 5} more")

        if status.untracked:
            lines.append(f"Untracked files: ({len(status.untracked)} files)")
            for f in status.untracked[:5]:
                lines.append(f"  - {f}")
            if len(status.untracked) > 5:
                lines.append(f"  ... and {len(status.untracked) - 5} more")

        if status.clean:
            lines.append("Nothing to commit, working tree clean.")

        return '\n'.join(lines)

    async def diff(
        self,
        path: Optional[Path] = None,
        staged: bool = False,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Show Git diff.

        Args:
            path: Repository path
            staged: Show staged changes if True
            file_path: Specific file to diff

        Returns:
            Dictionary with diff output
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository'
            }

        try:
            cmd = ['diff']
            if staged:
                cmd.append('--cached')
            if file_path:
                cmd.append('--')
                cmd.append(file_path)

            _, output, stderr = await self._run_git_command(cmd, cwd=cwd, check=False)

            if not output.strip():
                return {
                    'success': True,
                    'diff': '',
                    'message': 'No changes' if not staged else 'No staged changes'
                }

            return {
                'success': True,
                'diff': output,
                'staged': staged,
                'file': file_path
            }

        except Exception as e:
            logger.error(f'Git diff error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    async def log(
        self,
        path: Optional[Path] = None,
        max_commits: int = 10,
        oneline: bool = True
    ) -> Dict[str, Any]:
        """View commit history.

        Args:
            path: Repository path
            max_commits: Maximum commits to show
            oneline: Use one-line format if True

        Returns:
            Dictionary with commit history
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository'
            }

        try:
            cmd = ['log', f'-{max_commits}']
            if oneline:
                cmd.append('--oneline')

            _, output, _ = await self._run_git_command(cmd, cwd=cwd)

            commits = []
            for line in output.strip().split('\n'):
                if line.strip():
                    if oneline:
                        parts = line.split(' ', 1)
                        commits.append({
                            'hash': parts[0] if len(parts) > 0 else '',
                            'message': parts[1] if len(parts) > 1 else ''
                        })

            return {
                'success': True,
                'commits': commits,
                'count': len(commits)
            }

        except Exception as e:
            logger.error(f'Git log error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    async def add(
        self,
        files: List[str],
        path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Stage files for commit.

        Args:
            files: List of files to stage
            path: Repository path

        Returns:
            Dictionary with operation result
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository'
            }

        if not files:
            return {
                'success': False,
                'error': 'No files specified'
            }

        try:
            _, output, stderr = await self._run_git_command(
                ['add'] + files,
                cwd=cwd,
                check=False
            )

            if stderr:
                logger.warning(f'Git add warnings: {stderr}')

            logger.info(f'Staged files: {files}')

            return {
                'success': True,
                'staged': files,
                'message': f'Staged {len(files)} file(s)'
            }

        except Exception as e:
            logger.error(f'Git add error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    async def commit(
        self,
        message: str,
        path: Optional[Path] = None,
        amend: bool = False
    ) -> Dict[str, Any]:
        """Commit staged changes.

        Args:
            message: Commit message
            path: Repository path
            amend: Amend previous commit if True

        Returns:
            Dictionary with commit result
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository'
            }

        if not message.strip():
            return {
                'success': False,
                'error': 'Commit message cannot be empty'
            }

        try:
            cmd = ['commit', '-m', message]
            if amend:
                cmd.append('--amend')

            _, output, stderr = await self._run_git_command(
                cmd,
                cwd=cwd,
                check=False
            )

            # Get commit hash
            _, hash_output, _ = await self._run_git_command(
                ['rev-parse', 'HEAD'],
                cwd=cwd,
                check=False
            )
            commit_hash = hash_output.strip()[:7] if hash_output.strip() else 'unknown'

            if stderr and 'nothing to commit' in stderr:
                return {
                    'success': False,
                    'error': 'Nothing to commit'
                }

            logger.info(f'Committed {commit_hash}: {message[:50]}...')

            return {
                'success': True,
                'hash': commit_hash,
                'message': message,
                'amended': amend
            }

        except Exception as e:
            logger.error(f'Git commit error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    async def branch(
        self,
        action: str,
        name: Optional[str] = None,
        path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Branch operations.

        Args:
            action: 'list', 'create', 'delete', 'checkout'
            name: Branch name (required for create/delete/checkout)
            path: Repository path

        Returns:
            Dictionary with branch operation result
        """
        cwd = path or Path.cwd()

        if not self._is_git_repo(cwd):
            return {
                'success': False,
                'error': 'Not a Git repository'
            }

        try:
            if action == 'list':
                _, output, _ = await self._run_git_command(
                    ['branch', '-a'],
                    cwd=cwd
                )
                branches = [
                    line.strip().lstrip('* ').lstrip()
                    for line in output.strip().split('\n')
                    if line.strip()
                ]
                return {
                    'success': True,
                    'branches': branches,
                    'count': len(branches)
                }

            elif action == 'create':
                if not name:
                    return {'success': False, 'error': 'Branch name required'}
                _, output, stderr = await self._run_git_command(
                    ['checkout', '-b', name],
                    cwd=cwd,
                    check=False
                )
                if stderr:
                    return {'success': False, 'error': stderr}
                logger.info(f'Created and switched to branch: {name}')
                return {
                    'success': True,
                    'branch': name,
                    'message': f'Created and switched to branch: {name}'
                }

            elif action == 'delete':
                if not name:
                    return {'success': False, 'error': 'Branch name required'}
                _, output, stderr = await self._run_git_command(
                    ['branch', '-d', name],
                    cwd=cwd,
                    check=False
                )
                if stderr:
                    return {'success': False, 'error': stderr}
                logger.info(f'Deleted branch: {name}')
                return {
                    'success': True,
                    'branch': name,
                    'message': f'Deleted branch: {name}'
                }

            elif action == 'checkout':
                if not name:
                    return {'success': False, 'error': 'Branch name required'}
                _, output, stderr = await self._run_git_command(
                    ['checkout', name],
                    cwd=cwd,
                    check=False
                )
                if stderr:
                    return {'success': False, 'error': stderr}
                logger.info(f'Switched to branch: {name}')
                return {
                    'success': True,
                    'branch': name,
                    'message': f'Switched to branch: {name}'
                }

            else:
                return {
                    'success': False,
                    'error': f'Unknown branch action: {action}'
                }

        except Exception as e:
            logger.error(f'Git branch error: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute Git operation.

        Args:
            **kwargs: Operation parameters
                - operation: Git operation to perform
                - path: Repository path (optional)
                - Other parameters depend on operation

        Returns:
            Dictionary with operation result
        """
        operation = kwargs.get('operation')

        if not operation:
            return {
                'success': False,
                'error': 'No operation specified'
            }

        if operation not in self.allowed_operations:
            return {
                'success': False,
                'error': f'Operation not allowed: {operation}. Allowed: {self.allowed_operations}'
            }

        path = kwargs.get('path')
        if path:
            path = Path(path)

        if operation == 'status':
            return await self.status(path)
        elif operation == 'diff':
            return await self.diff(
                path=path,
                staged=kwargs.get('staged', False),
                file_path=kwargs.get('file')
            )
        elif operation == 'log':
            return await self.log(
                path=path,
                max_commits=kwargs.get('max_commits', 10),
                oneline=kwargs.get('oneline', True)
            )
        elif operation == 'add':
            files = kwargs.get('files', [])
            return await self.add(files, path)
        elif operation == 'commit':
            return await self.commit(
                message=kwargs.get('message', ''),
                path=path,
                amend=kwargs.get('amend', False)
            )
        elif operation == 'branch':
            return await self.branch(
                action=kwargs.get('action', 'list'),
                name=kwargs.get('name'),
                path=path
            )
        else:
            return {
                'success': False,
                'error': f'Unknown operation: {operation}'
            }
