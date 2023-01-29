"""Utilities for working with raw Compstate repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast, Iterable, List, overload
from typing_extensions import Literal, TypedDict

import yaml

from .comp import SRComp
from .match_period import Match
from .types import (
    Colour,
    DeploymentsData,
    LayoutData,
    RegionName,
    ScoreData,
    ShepherdingData,
    ShepherdName,
    TLA,
)

Commitish = str


class ShepherdInfo(TypedDict):
    name: ShepherdName
    colour: Colour
    regions: list[RegionName]
    teams: list[TLA]


class RawCompstate:
    """
    Helper class to interact with a Compstate as raw files in a Git repository
    on disk.

    :param Path path: The path to the Compstate repository.
    :param bool local_only: If true, this disabled the pulling, committing and
                            pushing functionality.
    """

    def __init__(self, path: str | Path, local_only: bool):
        self._path = Path(path)
        self._local_only = local_only

    # Load and save related functionality

    def load(self) -> SRComp:
        """Load the state as an ``SRComp`` instance."""
        return SRComp(self._path)

    def load_shepherds(self) -> list[ShepherdInfo]:
        """Load the shepherds' state."""

        layout = self.layout['teams']
        layout_map = {r['name']: r for r in layout}
        shepherds = cast(List[ShepherdInfo], self.shepherding['shepherds'])

        for s in shepherds:
            regions = s['regions']
            teams = []
            for region_name in regions:
                region = layout_map[region_name]
                teams += region['teams']
            s['teams'] = teams

            assert len(teams) == len(set(teams)), "Some teams listed in more than one region!"

        return shepherds

    def _get_score_path(self, match: Match) -> Path:
        """Get the path to the score file for the given match."""
        filename = f"{match.num:0>3}.yaml"
        path: Path = self._path / match.type.value / match.arena / filename
        return path

    def get_score_path(self, match: Match) -> str:
        """Get the path to the score file for the given match."""
        return str(self._get_score_path(match))

    def load_score(self, match: Match) -> ScoreData:
        """Load raw score data for the given match."""
        path = self._get_score_path(match)
        # Scores are basic data only
        with path.open() as fd:
            return cast(ScoreData, yaml.safe_load(fd))

    def save_score(self, match: Match, score: ScoreData) -> None:
        """Save raw score data for the given match."""
        path = self._get_score_path(match)

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(mode='w') as fd:
            yaml.safe_dump(score, fd, default_flow_style=False)

    @property
    def deployments(self) -> list[str]:
        deployments_path = self._path / 'deployments.yaml'

        with deployments_path.open() as dp:
            raw_deployments = cast(DeploymentsData, yaml.safe_load(dp))

        hosts = raw_deployments['deployments']
        return hosts

    @property
    def shepherding(self) -> ShepherdingData:
        """Provides access to the raw shepherding data.
           Most consumers actually want to use ``load_shepherds`` instead."""
        path = self._path / 'shepherding.yaml'

        with path.open() as shepherding_file:
            return cast(ShepherdingData, yaml.safe_load(shepherding_file))

    @property
    def layout(self) -> LayoutData:
        path = self._path / 'layout.yaml'

        with path.open() as layout_file:
            return cast(LayoutData, yaml.safe_load(layout_file))

    # Git repo related functionality

    @overload
    def git(
        self,
        command_pieces: Iterable[str],
        err_msg: str = '',
        *,
        return_output: Literal[True],
    ) -> str:
        ...

    @overload
    def git(
        self,
        command_pieces: Iterable[str],
        err_msg: str = '',
        return_output: Literal[False] = False,
    ) -> int:
        ...

    @overload
    def git(
        self,
        command_pieces: Iterable[str],
        err_msg: str = '',
        return_output: bool = False,
    ) -> str | int:
        ...

    def git(
        self,
        command_pieces: Iterable[str],
        err_msg: str = '',
        return_output: bool = False,
    ) -> str | int:
        command = ['git'] + list(command_pieces)

        if return_output:
            stderr: int | None = subprocess.STDOUT

            def func(*args: Any, **kwargs: Any) -> str:
                return cast(
                    str,
                    subprocess.check_output(*args, **kwargs).decode("utf-8"),
                )
        else:
            func = subprocess.check_call  # type: ignore[assignment]
            stderr = None

        try:
            return func(command, cwd=str(self._path), stderr=stderr)
        except subprocess.CalledProcessError as e:
            if err_msg:
                if e.output:
                    err_msg += '\n\n' + e.output.decode('utf-8')
                raise RuntimeError(err_msg) from e
            raise
        except OSError as e:
            if err_msg:
                raise RuntimeError(err_msg) from e
            raise

    @property
    def has_changes(self) -> bool:
        """
        Whether or not there are any changes to files in the state,
        including untracked files.
        """
        output = self.git(['status', '--porcelain'], return_output=True)
        return len(output) != 0

    def show_changes(self) -> None:
        self.git(['status'])

    def show_remotes(self) -> None:
        self.git(['remote', '-v'])

    def push(self, where: str, revspec: str, err_msg: str = '', force: bool = False) -> None:
        args = ['push', where, revspec]
        if force:
            args.insert(1, '--force')
        self.git(args, err_msg)

    def rev_parse(self, revision: Commitish) -> str:
        output = self.git(
            ['rev-parse', '--verify', revision],
            return_output=True,
            err_msg=f"Unknown revision '{revision}'.",
        )
        return output.strip()

    def has_commit(self, commit: Commitish) -> bool:
        """Whether or not the given commit is known to this repository."""
        try:
            self.rev_parse(commit + "^{commit}")
            return True
        except RuntimeError:
            return False

    def _is_parent(self, parent: Commitish, child: Commitish) -> bool:
        try:
            revspec = f'{parent}..{child}'
            revs = self.git(
                ['rev-list', '-n1', revspec, '--'],
                return_output=True,
            )
            # rev-list prints the revisions which are parents of 'child',
            # up to and including 'parent'; any output therefore tells us
            # that they're related
            return len(revs.strip()) != 0
        except subprocess.CalledProcessError:
            # One or both revisions are unknown
            return False

    def has_ancestor(self, commit: Commitish) -> bool:
        return self._is_parent(commit, 'HEAD')

    def has_descendant(self, commit: Commitish) -> bool:
        return self._is_parent('HEAD', commit)

    def get_default_branch(self) -> str:
        # Assume the default upstream is called 'origin'
        output = self.git(['remote', 'show', 'origin'], return_output=True)
        for line in output.splitlines():
            if line.strip().startswith('HEAD branch:'):
                _, branch = line.split(':')
                return branch.strip()
        raise RuntimeError("Unable to determine default branch")

    def reset_hard(self) -> None:
        self.git(['reset', '--hard', 'HEAD'], err_msg="Git reset failed.")

    def reset_and_fast_forward(self) -> None:
        self.reset_hard()

        self.pull_fast_forward()

    def pull_fast_forward(self) -> None:
        if self._local_only:
            return

        self.git(
            ['pull', '--ff-only', 'origin', self.get_default_branch()],
            err_msg="Git pull failed, deal with the merge manually.",
        )

    def stage(self, file_path: str) -> None:
        """
        Stage the given file.

        :param Path file_path: A path to the file to stage. This should
                              either be an absolute path, or one relative
                              to the compstate.
        """
        self.git(['add', file_path])

    def fetch(self, where: str = 'origin', quiet: bool = False) -> None:
        self.git(['fetch', where], return_output=quiet)

    def checkout(self, what: str) -> None:
        self.git(['checkout', what])

    def commit(self, commit_msg: str, allow_empty: bool = False) -> None:
        args = ['commit', '-m', commit_msg]
        if allow_empty:
            args += ['--allow-empty']
        self.git(args, return_output=True, err_msg="Git commit failed.")

    def commit_and_push(self, commit_msg: str, allow_empty: bool = False) -> None:
        self.commit(commit_msg, allow_empty)

        if self._local_only:
            return

        self.push(
            'origin',
            self.get_default_branch(),
            err_msg="Git push failed, deal with the merge manually.",
        )
