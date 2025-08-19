import time, re, os, ROOT
import numpy as np
import matplotlib.pyplot as plt


def eval_formula(formula, data_dict):
    if "[" not in formula: return data_dict[formula]

    def replace_index(match):
        var = match.group(1)
        idx = match.group(2)
        return f"uproot_dict['{var}'][:,{idx}]"

    pattern = re.compile(r"(\w+)\[(\d+)\]")
    numpy_expr = pattern.sub(replace_index, formula)

    result = eval(numpy_expr, {"uproot_dict": data_dict, "np": np})

    return result


def convert_root_cut_to_numpy_expr(cut_str, available_vars):
    # Replace && with & and || with |
    cut_str = cut_str.replace("&&", "&").replace("||", "|").replace("[", "[:, ")

    # Replace ROOT var names with uproot_dict["var"]
    pattern = re.compile(r'\b(' + '|'.join(re.escape(var) for var in available_vars) + r')\b')
    expr = pattern.sub(r'uproot_dict["\1"]', cut_str)

    comp_ops = ['>=', '<=', '==', '!=', '>', '<']
    for op in comp_ops:
        # Wrap expressions with comparison operators, avoiding double wrapping
        pattern = rf'(?<!\()([^\s&|()]+(?:\s*\[[^\]]+\])?\s*{re.escape(op)}\s*[^\s&|()]+)(?!\))'
        expr = re.sub(pattern, r'(\1)', expr)

    return expr


def plot(row, uproot_dict, outputfolder):
    name = row['name']
    f = ROOT.TFile(f"{outputfolder}/{name}.root", "recreate")
    f.cd()
    ROOT.gROOT.SetBatch(ROOT.kTRUE)

    c = ROOT.TCanvas(f"{name}_canvas")
    c.cd()

    # Handle ROOT-style cuts
    if str(row.cuts).strip() == "":
        first_key = next(iter(uproot_dict.keys()))
        mask = np.ones((uproot_dict[first_key].shape[0],), dtype=bool)
    else:
        expr = convert_root_cut_to_numpy_expr(str(row.cuts), uproot_dict.keys())
        mask = eval(expr)

    x = eval_formula(row.x, uproot_dict)[mask]
    nevents = x.shape[0]
    x = x.ravel()

    if str(row.y).strip() == "0" and str(row.z).strip() == "0":
        h = ROOT.TH1F(name, row.title, int(row.binsnx), float(row.binsminx), float(row.binsmaxx))
        h.FillN(len(x), x.astype(np.float64), np.ones_like(x, dtype=np.float64))
        h.Draw("HIST")
        h.SetFillColorAlpha(ROOT.kBlue, 0.2)
        h.SetLineColor(eval(f"ROOT.{row.color}"))
        binw = (float(row.binsmaxx) - float(row.binsminx)) / int(row.binsnx)
        h.GetXaxis().SetRangeUser(h.GetMean() - 3*h.GetRMS(), h.GetMean() + 3*h.GetRMS()) #iterative...
        h.GetXaxis().SetRangeUser(h.GetMean() - 3*h.GetRMS(), h.GetMean() + 3*h.GetRMS())
        h.GetXaxis().SetRangeUser(h.GetMean() - 5*h.GetRMS(), h.GetMean() + 5*h.GetRMS())
        h.GetYaxis().SetTitle(f"entries / {float(f'{binw:.1g}'):g} {row.ylabel}")
        c.Update()
        max_bin = h.GetMaximumBin()
        max_position = h.GetBinCenter(max_bin)
        max_value = h.GetBinContent(max_bin)
        bin1 = h.FindFirstBinAbove(max_value/2)
        bin2 = h.FindLastBinAbove(max_value/2)
        fwhm = h.GetBinCenter(bin2) - h.GetBinCenter(bin1)

        pave = ROOT.TPaveText(0.25, 0.7, 0.45, 0.88, "NDC")
        pave.SetFillColor(0)  # Transparent background
        pave.SetTextFont(42)
        pave.SetTextSize(0.03)
        pave.SetBorderSize(0)

        # Add three lines
        pave.AddText(f"Events in hist. = {h.Integral()}")
        pave.AddText(f"FWHM/2.35 = {fwhm/2.35:.3f}")
        pave.AddText(f"Peak at x = {max_position:.3f}")
        if max_position > 1000: pave.AddText(f"Ratio = {fwhm/max_position/2.35:.3f}")

        pave.Draw()

    elif str(row.y).strip() != "0" and str(row.z).strip() == "0":
        y = eval_formula(row.y, uproot_dict)[mask].ravel()

        print(name, row.title,
                      int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                      int(row.binsny), float(row.binsminy), float(row.binsmaxy))


        h = ROOT.TH2F(name, row.title,
                      int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                      int(row.binsny), float(row.binsminy), float(row.binsmaxy))
        h.FillN(len(x), x.astype(np.float64), y.astype(np.float64), np.ones_like(x, dtype=np.float64))
        h.Draw("ZCOL")
        h.GetYaxis().SetTitle(row.ylabel)

    else:
        y = eval_formula(row.y, uproot_dict)[mask].ravel()
        z = eval_formula(row.z, uproot_dict)[mask].ravel()

        h = ROOT.TH2D(name, row.title,
                            int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                            int(row.binsny), float(row.binsminy), float(row.binsmaxy))


        ROOT.gStyle.SetPalette(ROOT.kLightTemperature)
        h.FillN(len(x),
                x.astype(np.float64),
                y.astype(np.float64),
                z.astype(np.float64))
        h.Scale(1/nevents)
        h.Draw("ZCOL")
        h.SetContour(int(row.contours))
        h.GetZaxis().SetTitle(row.zlabel)
        h.GetYaxis().SetTitle(row.ylabel)
        h.GetXaxis().SetNdivisions(120)
        h.GetYaxis().SetNdivisions(120)
        c.SetGrid()
        c.SetLogz(int(row.logz))
        c.SetRightMargin(0.15)

    h.GetXaxis().SetTitle(row.xlabel)
    c.SaveAs(f"{outputfolder}/{name}.pdf")
    c.SaveAs(f"{outputfolder}/{name}.png")
    c.SaveAs(f"{outputfolder}/{name}.root")
    c.Write()
    h.Write()
    f.Close()
    c.Close()
    del c
    del h


