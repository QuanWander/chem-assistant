"""chemcore 核心测试（标准库 unittest，无第三方依赖）。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemcore import ChemError, acidbase, balance_equation, parse_formula, stoich
from chemcore.facts import activity_order, gas_test, ion_color, solubility_rules
from chemcore.knowledge import all_chapters, find_chapter


class FormulaTest(unittest.TestCase):
    def test_water(self):
        self.assertAlmostEqual(parse_formula("H2O").molar_mass(), 18.015, places=2)

    def test_sulfuric_acid(self):
        self.assertAlmostEqual(parse_formula("H2SO4").molar_mass(), 98.072, places=2)

    def test_calcium_hydroxide(self):
        self.assertAlmostEqual(parse_formula("Ca(OH)2").molar_mass(), 74.093, places=2)

    def test_aluminium_sulfate(self):
        self.assertAlmostEqual(parse_formula("Al2(SO4)3").molar_mass(), 342.15, places=1)

    def test_hydrate(self):
        self.assertAlmostEqual(parse_formula("CuSO4·5H2O").molar_mass(), 249.68, places=1)

    def test_complex_salt(self):
        self.assertAlmostEqual(parse_formula("K4[Fe(CN)6]").molar_mass(), 368.35, places=1)

    def test_charge(self):
        self.assertEqual(parse_formula("Fe^3+").charge, 3)
        self.assertEqual(parse_formula("SO4^2-").charge, -2)
        self.assertEqual(parse_formula("NH4^+").charge, 1)

    def test_counts(self):
        comp = parse_formula("Ca(OH)2")
        self.assertEqual(comp.counts, {"Ca": 1, "O": 2, "H": 2})

    def test_unknown_element(self):
        with self.assertRaises(ChemError) as ctx:
            parse_formula("Xx2O")
        self.assertEqual(ctx.exception.code, "UNKNOWN_ELEMENT")

    def test_bad_formula(self):
        with self.assertRaises(ChemError):
            parse_formula("H2O)")
        with self.assertRaises(ChemError):
            parse_formula("")


class EquationTest(unittest.TestCase):
    def coeffs(self, text):
        return [sp.coefficient for sp in balance_equation(text).species]

    def test_water(self):
        self.assertEqual(self.coeffs("H2 + O2 -> H2O"), [2, 1, 2])

    def test_magnetite(self):
        self.assertEqual(self.coeffs("Fe + O2 -> Fe3O4"), [3, 2, 1])

    def test_propane(self):
        self.assertEqual(self.coeffs("C3H8 + O2 -> CO2 + H2O"), [1, 5, 3, 4])

    def test_aluminium_hcl(self):
        self.assertEqual(self.coeffs("Al + HCl -> AlCl3 + H2"), [2, 6, 2, 3])

    def test_precipitation(self):
        self.assertEqual(self.coeffs("CuSO4 + NaOH -> Cu(OH)2 + Na2SO4"), [1, 2, 1, 1])

    def test_ionic(self):
        self.assertEqual(self.coeffs("Fe^3+ + OH^- -> Fe(OH)3"), [1, 3, 1])

    def test_ion_charge(self):
        self.assertEqual(self.coeffs("Ag^+ + Cl^- -> AgCl"), [1, 1, 1])

    def test_permanganate(self):
        self.assertEqual(
            self.coeffs("KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O"),
            [2, 16, 2, 2, 5, 8],
        )

    def test_state_symbols_ignored(self):
        self.assertEqual(self.coeffs("H2(g) + O2(g) -> H2O(l)"), [2, 1, 2])

    def test_impossible(self):
        with self.assertRaises(ChemError) as ctx:
            balance_equation("C + O2 -> CO2 + H2O")
        self.assertIn(ctx.exception.code, {"NO_SOLUTION", "MULTIPLE_SOLUTIONS"})

    def test_missing_arrow(self):
        with self.assertRaises(ChemError) as ctx:
            balance_equation("H2 + O2")
        self.assertEqual(ctx.exception.code, "NO_ARROW")


class StoichTest(unittest.TestCase):
    def test_moles_from_mass(self):
        self.assertAlmostEqual(stoich.moles_from_mass(18.0, "H2O"), 1.0, places=2)

    def test_mass_from_moles(self):
        self.assertAlmostEqual(stoich.mass_from_moles(2, "H2O"), 36.03, places=1)

    def test_gas_volume(self):
        self.assertAlmostEqual(stoich.gas_volume_stp(2), 44.8, places=3)

    def test_concentration(self):
        self.assertAlmostEqual(stoich.concentration(0.5, 2), 0.25, places=6)

    def test_dilution(self):
        result = stoich.dilute(c1=2, v1=0.5, c2=1)
        self.assertAlmostEqual(result["v2"], 1.0, places=6)

    def test_yield(self):
        self.assertAlmostEqual(stoich.percent_yield(90, 100), 90.0, places=6)

    def test_limiting_reagent(self):
        result = stoich.limiting_reagent([("H2", 2), ("O2", 0.5)], "H2 + O2 -> H2O")
        self.assertEqual(result["limiting"], "O2")

    def test_negative_rejected(self):
        with self.assertRaises(ChemError):
            stoich.moles_from_mass(-1, "H2O")


class AcidBaseTest(unittest.TestCase):
    def test_strong_acid(self):
        self.assertAlmostEqual(acidbase.ph_strong_acid(0.1).ph, 1.0, places=6)

    def test_strong_base(self):
        self.assertAlmostEqual(acidbase.ph_strong_base(0.1).ph, 13.0, places=6)

    def test_weak_acid(self):
        r = acidbase.ph_weak_acid(0.1, 1.8e-5)
        self.assertAlmostEqual(r.ph, 2.875, places=2)
        self.assertIn("c/Ka", "".join(r.assumptions))

    def test_weak_base(self):
        r = acidbase.ph_weak_base(0.1, 1.8e-5)
        self.assertAlmostEqual(r.ph, 11.125, places=2)

    def test_missing_ka(self):
        with self.assertRaises(ChemError):
            acidbase.ph_weak_acid(0.1, 0)


class FactsTest(unittest.TestCase):
    def test_elements(self):
        from chemcore.facts import elements

        self.assertEqual(len(elements()), 92)
        self.assertAlmostEqual(elements()["C"]["mass"], 12.011, places=3)

    def test_activity(self):
        order = activity_order()
        self.assertLess(order.index("Zn"), order.index("Cu"))
        self.assertIn("H", order)

    def test_ion_color(self):
        self.assertEqual(ion_color("Cu2+"), "蓝色")

    def test_gas_test(self):
        self.assertIn("复燃", gas_test("O2")["phenomenon"])

    def test_solubility_rules(self):
        self.assertTrue(any("BaSO4" in rule for rule in solubility_rules()))


class KnowledgeTest(unittest.TestCase):
    def test_catalog_not_empty(self):
        chapters = all_chapters()
        self.assertGreater(len(chapters), 20)
        self.assertTrue(any("必修第一册" == c["book"] for c in chapters))

    def test_find(self):
        hits = find_chapter("化学方程式")
        self.assertTrue(any("第五单元" in h["chapter"] for h in hits))


if __name__ == "__main__":
    unittest.main(verbosity=2)
