"""Reference lamina data for the application, stored in SI units.

The two datasets are the classic T300/5208 graphite/epoxy and Scotchply 1002
glass/epoxy values (Tsai & Hahn; Kaw), taken here from Martinez & Bishay (2021),
Table 2. They are literature reference values, not qualified design allowables.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialRecord:
    name: str
    E1: float
    E2: float
    G12: float
    v12: float
    ply_thickness: float
    reference: str
    source_url: str
    reference_note: str
    Xt: float
    Xc: float
    Yt: float
    Yc: float
    S: float

    def as_core_material(self) -> dict[str, float]:
        return {"E1": self.E1, "E2": self.E2, "G12": self.G12, "v12": self.v12}

    def as_strengths(self) -> dict[str, float]:
        return {"Xt": self.Xt, "Xc": self.Xc, "Yt": self.Yt, "Yc": self.Yc, "S": self.S}


DEFAULT_MATERIALS: dict[str, MaterialRecord] = {
    "Graphite/Epoxy (T300/5208)": MaterialRecord(
        name="Graphite/Epoxy (T300/5208)",
        E1=181e9,
        E2=10.3e9,
        G12=7.17e9,
        v12=0.28,
        ply_thickness=0.125e-3,
        reference="Martinez & Bishay (2021), Composites Part C, Table 2 (graphite/epoxy).",
        source_url="https://www.csun.edu/~pbishay/pubs/Martinez_Bishay_CPC_2020.pdf",
        reference_note=(
            "Classic T300/5208 lamina values (Tsai & Hahn; Kaw). "
            "The 0.125 mm ply thickness is a typical prepreg value chosen for illustration."
        ),
        Xt=1500e6, Xc=1500e6, Yt=40e6, Yc=246e6, S=68e6,
    ),
    "Glass/Epoxy (Scotchply 1002)": MaterialRecord(
        name="Glass/Epoxy (Scotchply 1002)",
        E1=38.6e9,
        E2=8.27e9,
        G12=4.14e9,
        v12=0.26,
        ply_thickness=0.125e-3,
        reference="Martinez & Bishay (2021), Composites Part C, Table 2 (glass/epoxy).",
        source_url="https://www.csun.edu/~pbishay/pubs/Martinez_Bishay_CPC_2020.pdf",
        reference_note=(
            "Classic Scotchply 1002 lamina values (Tsai & Hahn; Kaw). "
            "The 0.125 mm ply thickness is chosen for illustration."
        ),
        Xt=1062e6, Xc=610e6, Yt=31e6, Yc=118e6, S=72e6,
    ),
}
