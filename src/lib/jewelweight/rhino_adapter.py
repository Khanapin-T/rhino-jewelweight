"""Rhino side: picking objects and turning them into calc.ObjectCheck records."""

import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import scriptcontext as sc

from . import calc

# rhinoscriptsyntax filter bits: surface 8, polysurface 16, mesh 32,
# SubD 262144, extrusion 1073741824. Single surfaces are allowed because a
# closed single-face brep (e.g. a sphere) is a valid solid. SubD is pickable
# only to be reported as unsupported with a hint.
_PICK_FILTER = 8 | 16 | 32 | 262144 | 1073741824

_PICK_PROMPT = "Выберите изделие (полиповерхности, extrusion, меши) и нажмите Enter"


def active_doc():
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        raise calc.UserError("Нет активного документа Rhino.")
    sc.doc = doc  # rhinoscriptsyntax works on scriptcontext.doc
    return doc


def pick_objects():
    """Let the user pick objects; preselected objects are accepted.

    Returns a list of object ids, empty if the user cancelled.
    """
    try:
        Rhino.RhinoApp.SetFocusToMainWindow()
    except Exception:
        pass  # focus is only a convenience
    ids = rs.GetObjects(_PICK_PROMPT, filter=_PICK_FILTER, group=True,
                        preselect=True, select=False)
    return list(ids) if ids else []


def _volume(geometry):
    props = rg.VolumeMassProperties.Compute(geometry)
    return None if props is None else props.Volume


def _mesh_is_manifold(mesh):
    # The overload has out parameters; Rhino's Python 3 returns
    # (result, isOriented, hasBoundary), as rhinoscriptsyntax relies on.
    result = mesh.IsManifold(True)
    if isinstance(result, tuple):
        result = result[0]
    return bool(result)


def _cleaned_copy(mesh):
    """Copy without duplicate and collapsed faces; returns (copy, faces removed)."""
    copy = mesh.DuplicateMesh()
    before = copy.Faces.Count
    copy.Vertices.CombineIdentical(True, True)
    copy.Faces.CullDegenerateFaces()
    copy.Faces.ExtractDuplicateFaces()
    copy.Compact()
    return copy, before - copy.Faces.Count


def _log_mesh_report(object_id, mesh):
    """Write Rhino's own mesh check (as in _Check) to the command line."""
    try:
        log = Rhino.FileIO.TextLog()
        mesh.Check(log, rg.MeshCheckParameters.Defaults())
        report = log.ToString()
    except Exception as err:
        report = "не удалось получить отчёт: {0}".format(err)
    Rhino.RhinoApp.WriteLine("JewelWeight: меш {0} не прошёл проверку manifold. Отчёт Rhino:\n{1}"
                             .format(object_id, report))


def _inspect_mesh(object_id, mesh):
    closed = mesh.IsClosed
    manifold = _mesh_is_manifold(mesh)
    removed = 0
    if closed and not manifold:
        # Exported STL often has duplicate or collapsed triangles: they make
        # edges non-manifold but add nothing to the volume. Check a clean copy.
        copy, removed = _cleaned_copy(mesh)
        if copy.IsClosed and _mesh_is_manifold(copy):
            mesh, manifold = copy, True
        else:
            removed = 0
            _log_mesh_report(object_id, mesh)
    return calc.ObjectCheck(
        object_id, calc.KIND_MESH,
        is_closed=closed,
        is_manifold=manifold,
        volume=_volume(mesh) if closed and manifold else None,
        repaired_faces=removed)


def inspect_object(doc, object_id):
    """Collect closedness, manifoldness and signed volume of one object."""
    rh_object = doc.Objects.FindId(object_id)
    if rh_object is None or rh_object.IsDeleted:
        return calc.ObjectCheck(object_id, calc.KIND_DELETED)

    geometry = rh_object.Geometry
    if isinstance(geometry, rg.Extrusion):
        geometry = geometry.ToBrep(False)

    if isinstance(geometry, rg.Brep):
        solid = geometry.IsSolid
        manifold = geometry.IsManifold
        # IsSolid is also false for every non-manifold brep; report only
        # "non-manifold" then, not "open" as well.
        return calc.ObjectCheck(
            object_id, calc.KIND_BREP,
            is_closed=solid or not manifold,
            is_manifold=manifold,
            volume=_volume(geometry) if solid else None)

    if isinstance(geometry, rg.Mesh):
        return _inspect_mesh(object_id, geometry)

    type_name = geometry.GetType().Name if geometry is not None else "?"
    return calc.ObjectCheck(object_id, calc.KIND_UNSUPPORTED, type_name=type_name)


def mm3_factor(doc):
    """Factor from document units cubed to mm3."""
    units = doc.ModelUnitSystem
    unit_name = units.ToString()
    scale = None
    if unit_name not in calc.UNSUPPORTED_UNITS:
        scale = Rhino.RhinoMath.UnitScale(units, Rhino.UnitSystem.Millimeters)
    return calc.mm3_factor(unit_name, scale)


def highlight(doc, object_ids):
    """Select only the given objects so the user sees which ones failed."""
    doc.Objects.UnselectAll()
    for object_id in object_ids:
        doc.Objects.Select(object_id, True)
    doc.Views.Redraw()
