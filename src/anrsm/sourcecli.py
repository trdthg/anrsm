import typer
from anrsm.config.config import settings
from typing_extensions import Annotated
from typing import Optional
from rich.progress import track
import os
from anrsm.source.source import find_source_id
from rich import print
import platform

app = typer.Typer()

@app.command("update")
def source_update(sourceurl: Annotated[Optional[str], typer.Argument(help="Set this item if you wish to use this source temporarily.")] = None):
    """
    Update the source file.
    """
    if sourceurl != None:
        settings.set("sourceurl",sourceurl)
    import requests
    resp=requests.get(settings["sourceurl"],stream=True)
    with open(os.path.join(settings["cargocache"],"source.json"),'wb') as file:
        for data in track(resp.iter_content(chunk_size=1024), description="Updating..."):
            file.write(data)
    print("Susscessfully update.")

@app.command("list")
def source_list():
    """
    List all package.
    """
    from rich.console import Console
    from rich.table import Table
    with open(os.path.join(settings["cargocache"],"source.json"),'r') as file:
        table = Table(title="Available Package")
        table.add_column("Name", style="yellow")
        table.add_column("Version", style="white")        
        table.add_column("Architecture", justify="left", style="green")
        table.add_column("Source Type", style="green")
        import json
        info=json.load(file)        
        for data in track(info, description="Parsing..."):
            table.add_row(data['name'],data['version'], data['arch'],', '.join(data['tag']))
        console = Console()
        console.print(table)

@app.command("info")
def source_info(name: Annotated[str, typer.Argument(help="the package name you want to look inside.",metavar="PackageName")], arch: Annotated[str, typer.Argument(default_factory=platform.machine,metavar="Architecture")],ver: Annotated[Optional[str], typer.Option("--version",metavar="Version")] = None):
    """
    Print the detailed information for package.
    """
    from rich import print
    id=find_source_id(name,ver,arch)
    if id==-1:
        print("[bold red]Error[/bold red]: No matches found. :boom:")
        raise typer.Exit()
    with open(os.path.join(settings["cargocache"],"source.json"),'r') as file:
        import json
        info=json.load(file)
        print(f"Name: {info[id]['name']}")
        print(f"Version: {info[id]['version']}")
        print(f"Version Code: {info[id]['versioncode']}")
        print(f"Source Type: {', '.join(info[id]['tag'])}")
        print(f"Description: {info[id]['desc']}")
        print(f"Origin: {info[id]['origin']}")
        print(f"Arch: {info[id]['arch']}")
        print(f"To cache this package, use `anrsm source cache {info[id]['name']} {info[id]['arch']} --version {info[id]['version']}")

@app.command("cache")
def source_install(name: Annotated[str, typer.Argument(help="the package name you want to look inside.",metavar="PackageName")], arch: Annotated[str, typer.Argument(default_factory=platform.machine,metavar="Architecture")],ver: Annotated[Optional[str], typer.Option("--version",metavar="Version")] = None):
    """
    Download a package.
    """
    id=find_source_id(name,ver,arch)
    if id==-1:
        print("[bold red]Error[/bold red]: No matches found. :boom:")
        raise typer.Exit()
    # check if cached
    cached=False
    with open(os.path.join(settings["cargocache"],"source.json"),'r') as file:
        import json
        info=json.load(file)        
        if not sourcache_check(id):
            import requests
            resp=requests.get(info[id]["files"]["source"]["url"],stream=True)
            with open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["source"]["sha256"]),'wb') as file:
                for data in track(resp.iter_content(chunk_size=1024), description="Downloading Source Zip..."):
                    file.write(data)
        if not metacache_check(id):
            import requests
            resp=requests.get(info[id]["files"]["manifest"]["url"],stream=True)
            with open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["manifest"]["sha256"]),'wb') as file:
                for data in track(resp.iter_content(chunk_size=1024), description="Downloading Manifest..."):
                    file.write(data)

@app.command("expand")
def source_expand(code: Annotated[str, typer.Argument(help="the package name you want to look inside.",metavar="PackageName")], arch: Annotated[str, typer.Argument(default_factory=platform.machine,metavar="Architecture")],dest: Annotated[str, typer.Argument(help="the destination you want to put this package to.",metavar="Destination")],ver: Annotated[Optional[str], typer.Option("--version",metavar="Version")] = None,softlink: Annotated[bool,typer.Option(help="Build softlink")] = False):
    """
    Expand package.
    """
    id=find_source_id(code)
    if id==-1:
        print("[bold red]Error[/bold red]: No matches found. :boom:")
        raise typer.Exit()
    # check if cached
    with open(os.path.join(settings["cargocache"],"source.json"),'r') as file:
        import json
        info=json.load(file)
        if not sourcache_check(id):
            print("[bold red]Error[/bold red]: No Source Zip cache found. Please cache it first. :boom:")
            raise typer.Exit()
        if not metacache_check(id):
            print("[bold red]Error[/bold red]: No Manifest cache found. Please cache it first. :boom:")
            raise typer.Exit()
        
        with open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["manifest"]["sha256"])) as mani:
            import json
            mmm=json.load(mani)
            if mmm["compression"]=="zip":
                import zipfile
                with zipfile.ZipFile(os.path.join(settings["cargocache"],"cache",info[id]["files"]["source"]["sha256"]), 'r') as file:
                    file.extractall(dest)
            elif mmm["compression"]=="targz":
                import tarfile
                with tarfile.open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["source"]["sha256"]),mode="r:gz") as tf:
                    tf.extractall(dest)
            elif mmm["compression"]=="tarxz":
                import tarfile
                with tarfile.open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["source"]["sha256"]),mode="r:xz") as tf:
                    tf.extractall(dest)
            elif mmm["compression"]=="tarbz2":
                import tarfile
                with tarfile.open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["source"]["sha256"]),mode="r:bz2") as tf:
                    tf.extractall(dest)
        
        if softlink:
            with open(os.path.join(settings["cargocache"],"cache",info[id]["files"]["manifest"]["sha256"])) as mani:
                import json
                mmm=json.load(mani)
                for link in track(mmm['softlink'], description="Building softlink..."):
                    print(f"[green]Info:  {os.path.join(settings['softlink'],link['from'])} [grey]->[/grey] {os.path.join(dest,link['to'])}")
                    os.symlink(os.path.join(dest,link['to']),os.path.join(settings['softlink'],link['from']))

if __name__ == "__main__":
    app()