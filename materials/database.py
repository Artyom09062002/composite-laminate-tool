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
    alpha1: float
    alpha2: float
    thermal_reference_temperature_c: float
    thermal_reference_basis: str
    cte_reference: str
    cte_source_url: str
    temperature_reference: str
    temperature_source_url: str

    def as_core_material(self) -> dict[str, float]:
        return {"E1": self.E1, "E2": self.E2, "G12": self.G12, "v12": self.v12}

    def as_thermal_core_material(self) -> dict[str, float]:
        """Core elastic properties plus sourced principal-axis CTEs [1/K]."""
        return {**self.as_core_material(), "alpha1": self.alpha1, "alpha2": self.alpha2, "alpha12": 0.0}

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
        alpha1=0.02e-6,
        alpha2=22.5e-6,
        thermal_reference_temperature_c=121.11111111111111,
        thermal_reference_basis="Measured stress-free reference selected for residual-stress analysis (250 °F); nominal cure was 350 °F.",
        cte_reference="C. B. York (2015), Influence of Bending–Twisting Coupling on Compression Buckling Strength, Table 2.",
        cte_source_url="https://eprints.gla.ac.uk/105827/1/105827.pdf",
        temperature_reference="Kriz, Stinchcomb & Tenney, NASA-CR-162921 (1980): measured range 250–300 °F; 250 °F selected for analysis.",
        temperature_source_url="https://ntrs.nasa.gov/citations/19800012968",
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
        alpha1=8.6e-6,
        alpha2=22.1e-6,
        thermal_reference_temperature_c=165.55555555555554,
        thermal_reference_basis="Manufacturer press-cure temperature (330 °F); no measured stress-free temperature was found.",
        cte_reference="C. B. York (2015), Influence of Bending–Twisting Coupling on Compression Buckling Strength, Table 2.",
        cte_source_url="https://eprints.gla.ac.uk/105827/1/105827.pdf",
        temperature_reference="3M, Scotchply Reinforced Plastic Type 1002 technical data, §1.8 cure cycles: press cure at 330 °F.",
        temperature_source_url="https://digital.library.unt.edu/ark:/67531/metadc1064666/m2/1/high_res_d/5389797.pdf",
    ),
}
