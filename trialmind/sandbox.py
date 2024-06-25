"""
Implement utils on intialize cloud sandbox to support
code execution and data exploration.
"""

import os
import pdb
from typing import List, Union
import pathlib

from e2b_code_interpreter import CodeInterpreter

from typing import List, Union, Literal
from pydantic import BaseModel

class Dataframe(BaseModel):
    dataframe_id: str = None # unique identifier of the dataframe
    path: str = None # remote path (in the sandbox) or local path of the data
    table_name: str = None # name of the table, e.g., "adsl"
    data_schema: str = None # schema description of the data

    def __str__(self) -> str:
        return f"""Dataframe schema <{self.data_schema}>"""
    
class Artifact(BaseModel):
    content: Union[bytes,str] = None # content of the artifact in bytes (like img) or string (like txt, html)
    file_name: str = None # the name of the artifact
    file_path: str = None # the path of the artifact in the local file system
    file_type: str = None # type of the artifact, e.g., "image", "csv", "json", "html", "pdf"

    def __str__(self) -> str:
        return f"""Artifact <{self.file_name}>"""

class E2BSandbox:
    """A sandbox for running code and data exploration.
    Every time we call this API, it creates a sandbox and keep that sandbox alive for 3 minutes by default.
    If we call this API again within 3 minutes, it will use the same sandbox, 
    and extend the life of the sandbox for another 3 minutes.
    Otherwise, it will create a new sandbox.

    Args:
        sandbox_id (str, optional): The ID of the sandbox to connect to. If not given, a new sandbox will be created.
        alive_time (int, optional): The time to keep the sandbox alive in seconds. Defaults to 3*60 seconds.
    """
    _uploaded_files = [] # store the uploaded files
    sandbox = None # store the sandbox object
    def __init__(
        self, 
        sandbox_id: str = None,
        alive_time: int = 3*60,
        ):
        if sandbox_id is not None:
            self.connect_to_sandbox(sandbox_id)
        else:
            self.create_sandbox()
        
        # keep alive for 3 minutes
        self.sandbox.keep_alive(alive_time)

    @property
    def sandbox_id(self) -> str:
        return self.sandbox.id

    @property
    def uploaded_files_description(self) -> str:
        if len(self._uploaded_files) == 0:
            return ""
        lines = ["The following files available in the sandbox:"]
        for file in self._uploaded_files:
            # remote path: /home/user/xxx.csv
            remote_path = file["remote_path"]
            desc = file["description"]

            if file.description == "":
                lines.append(f"- path: `{remote_path}`")

            else:
                lines.append(f"- path: `{remote_path}`, description: {desc}")
        return "\n".join(lines)

    def run_python(self, code: str):
        """Run Python code in the sandbox.

        Args:
            code (str): The Python code to run.

        Returns:
            tuple: A tuple of (stdout, stderr, artifacts).
        """
        # before run, check the file list in the sandbox
        all_files = self.listdir()
        stdout, stderr, artifacts =  self.sandbox.run_python(code)

        # download all the artifacts
        generated_artifacts = []
        artifact_names = []
        if len(artifacts) > 0:
            for artifact in artifacts:
                file_in_bytes = artifact.download()
                filename = artifact.name
                filetype = pathlib.Path(filename).suffix
                artifact = Artifact(
                    content=file_in_bytes,
                    file_name=filename,
                    file_type=filetype,
                )
                generated_artifacts.append(artifact)
                artifact_names.append(filename)

        # check and only keep the generated files which are not in artifacts
        # after run, check the file list in the sandbox
        generated_files = list(set(self.listdir()) - set(all_files))
        generated_files = [g for g in generated_files if g not in artifact_names]
        if len(generated_files) > 0:
            for file in generated_files:
                filename = os.path.basename(file)
                filetype = pathlib.Path(filename).suffix
                if filetype != "": # not a folder
                    file_in_bytes = self.download_file(file)
                    artifact = Artifact(
                        content=file_in_bytes,
                        file_name=filename,
                        file_type=filetype,
                    )
                    generated_artifacts.append(artifact)

        return stdout, stderr, generated_artifacts

    def listdir(self, folder="/home/user"):
        # list the files in the sandbox
        content = self.sandbox.filesystem.list(folder)
        all_content = [os.path.join(folder, file.name) for file in content]
        return all_content

    def download_file(self, path):
        file_in_bytes = self.sandbox.download_file(path)
        return file_in_bytes

    def create_sandbox(self):
        """Create a new sandbox.
        """
        # Create a new sandbox
        self.sandbox = CodeInterpreter()

    def close_sandbox(self):
        """Close the current sandbox.
        """
        self.sandbox.close()

    def connect_to_sandbox(self, sandbox_id: str):
        """Connect to an existing sandbox.
        """
        self.sandbox = CodeInterpreter.reconnect(sandbox_id)

    def download_artifacts(self, artifacts):
        """Download an artifact from the sandbox.

        Args:
            artifacts: The list of artifact to download.

        Returns:
            bytes: The content of the artifact.
        """
        download_charts = []
        for artifact in artifacts:
            downloaded = artifact.download()
            filename = artifact.name
            filename = os.path.basename(filename)
            filetype = pathlib.Path(filename).suffix
            artifact = Artifact(
                content=downloaded,
                file_name=filename,
                file_type=filetype,
            )
            download_charts.append(artifact)
        return download_charts
    
    def upload_file(self, file_path: str, description: str = ""):
        """Upload a file to the sandbox.

        Args:
            file_path (str): The path to the file to upload.
        """
        with open(file_path, "r") as file:
            remote_path = self.sandbox.upload_file(file)
        
        self._uploaded_files.append(
            {
                "remote_path": remote_path,
                "description": description,
                "name": os.path.basename(file_path),
            }
        )
        return remote_path

    def download_file(self, remote_path: str):
        return self.sandbox.download_file(remote_path)

    def install_python_packages(self, package_names: Union[str, List[str]]):
        self.sandbox.install_python_packages(package_names)

    def install_system_packages(self, package_names: Union[str, List[str]]):
        self.sandbox.install_system_packages(package_names)