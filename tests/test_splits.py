import pandas as pd
import pytest

from oculens.data.splits import check_no_leakage, cross_site_split, grouped_split


def toy(n_groups=60, per_group=3):
    rows = []
    for g in range(n_groups):
        for i in range(per_group):
            rows.append({"group": f"p{g}", "label": ["A", "B", "C"][g % 3], "site": "S1" if g < 40 else "S2"})
    return pd.DataFrame(rows)


def test_grouped_split_has_no_leakage_and_all_parts():
    df = toy()
    split = grouped_split(df)
    check_no_leakage(df, split)
    assert set(split) == {"train", "val", "test"}


def test_cross_site_holds_out_whole_site():
    df = toy()
    split = cross_site_split(df, test_site="S2")
    assert (split[df["site"] == "S2"] == "test").all()
    assert not (split[df["site"] == "S1"] == "test").any()
    check_no_leakage(df, split)


def test_leakage_is_detected():
    df = pd.DataFrame({"group": ["a", "a"], "label": ["x", "x"]})
    with pytest.raises(ValueError):
        check_no_leakage(df, pd.Series(["train", "test"]))
