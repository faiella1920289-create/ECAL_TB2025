import time, re, os, ROOT
import numpy as np
import traceback
import shutil

def replace_index_axis1(match):
    var = match.group(1)
    idx = match.group(2)
    return f"uproot_dict['{var}'][:,{idx}]"

def replace_index_noch(match):
    var = match.group(1)
    return f"uproot_dict['{var}']"

def eval_formula(formula, data_dict):
    if "(" in formula and "[" not in formula:
      pattern = re.compile(r"(\w+)")
      numpy_expr = pattern.sub(replace_index_noch, formula)
      print(numpy_expr)
      result = eval(numpy_expr, {"uproot_dict": data_dict, "np": np})

      return result


    if "[" not in formula: return data_dict[formula]

    #if "[" not in formula: eval(formula, {"uproot_dict": data_dict, "np": np})

    pattern = re.compile(r"(\w+)\[(\d+)\]")
    numpy_expr = pattern.sub(replace_index_axis1, formula)
    print(numpy_expr)
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


def plot(row, uproot_dict, outputfolder, just_draw=False):

  ROOT.gErrorIgnoreLevel = ROOT.kError

  try:
    name = row['name']

    print(name)

    os.makedirs(f"{outputfolder}/{row.folder}/", exist_ok=True)

    f = ROOT.TFile(f"{outputfolder}/{row.folder}/{name}.root", ("update" if just_draw else "recreate"))
    f.cd()

    ROOT.gROOT.SetBatch(ROOT.kTRUE)

    if just_draw:
      for key in f.GetListOfKeys():
        obj = key.ReadObj()
        try:
          if obj.InheritsFrom("TCanvas"):
            f.Delete(f"{key.GetName()};{key.GetCycle()}")
        except TypeError:
          pass

    c = ROOT.TCanvas(f"{name}_canvas")
    c.cd()

    if just_draw:
      pass
    else:
      if str(row.cuts).strip() == "":
        first_key = next(iter(uproot_dict.keys()))
        mask = np.ones((uproot_dict[first_key].shape[0],), dtype=bool)
      else:
        expr = convert_root_cut_to_numpy_expr(str(row.cuts), uproot_dict.keys())
        print(expr)
        mask = eval(expr)

      x = eval_formula(row.x, uproot_dict)[mask]
      nevents = x.shape[0]
      x = x.ravel()

    if str(row.y).strip() == "0" and str(row.z).strip() == "0":
        if just_draw:
          h = f.Get(f"{name}")
        else:
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
        c.SetLogy(int(row.logy))

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
        if just_draw:
          h = f.Get(f"{name}")
        else:
          y = eval_formula(row.y, uproot_dict)[mask].ravel()
          h = ROOT.TH2F(name, row.title,
                      int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                      int(row.binsny), float(row.binsminy), float(row.binsmaxy))
          print(x.shape, y.shape)
          h.FillN(len(x), x.astype(np.float64), y.astype(np.float64), np.ones_like(x, dtype=np.float64))

        h.Draw("ZCOL")
        h.GetYaxis().SetTitle(row.ylabel)

        h.GetXaxis().SetRangeUser(h.GetMean(1) - 3*h.GetRMS(1), h.GetMean(1) + 3*h.GetRMS(1)) #iterative...
        h.GetXaxis().SetRangeUser(h.GetMean(1) - 3*h.GetRMS(1), h.GetMean(1) + 3*h.GetRMS(1))
        h.GetXaxis().SetRangeUser(h.GetMean(1) - 5*h.GetRMS(1), h.GetMean(1) + 5*h.GetRMS(1))
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 3*h.GetRMS(2), h.GetMean(2) + 3*h.GetRMS(2)) #iterative...
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 3*h.GetRMS(2), h.GetMean(2) + 3*h.GetRMS(2))
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 5*h.GetRMS(2), h.GetMean(2) + 5*h.GetRMS(2))

    else:
        ROOT.gStyle.SetPalette(ROOT.kLightTemperature)

        if just_draw:
          h = f.Get(f"{name}")
        else:
          y = eval_formula(row.y, uproot_dict)[mask].ravel()
          z = eval_formula(row.z, uproot_dict)[mask].ravel()

          h = ROOT.TH2D(name, row.title,
                            int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                            int(row.binsny), float(row.binsminy), float(row.binsmaxy))


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
        c.SetRightMargin(0.15)
        h.GetXaxis().SetRangeUser(h.GetMean(1) - 3*h.GetRMS(1), h.GetMean(1) + 3*h.GetRMS(1)) #iterative...
        h.GetXaxis().SetRangeUser(h.GetMean(1) - 3*h.GetRMS(1), h.GetMean(1) + 3*h.GetRMS(1))
        h.GetXaxis().SetRangeUser(h.GetMean(1) - 5*h.GetRMS(1), h.GetMean(1) + 5*h.GetRMS(1))
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 3*h.GetRMS(2), h.GetMean(2) + 3*h.GetRMS(2)) #iterative...
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 3*h.GetRMS(2), h.GetMean(2) + 3*h.GetRMS(2))
        h.GetYaxis().SetRangeUser(h.GetMean(2) - 5*h.GetRMS(2), h.GetMean(2) + 5*h.GetRMS(2))


    h.GetXaxis().SetTitle(row.xlabel)

    if not os.path.exists(f"{outputfolder}/{row.folder}/index.php"):
      shutil.copy2(f"{outputfolder}/index.php", f"{outputfolder}/{row.folder}/index.php")
    if not os.path.exists(f"{outputfolder}/{row.folder}/jsroot_viewer.php"):
      shutil.copy2(f"{outputfolder}/jsroot_viewer.php", f"{outputfolder}/{row.folder}/jsroot_viewer.php")

    #c.SaveAs(f"{outputfolder}/{row.folder}/{name}.pdf")
    c.SaveAs(f"{outputfolder}/{row.folder}/{name}.png")
    if just_draw: c.Write("", ROOT.TObject.kOverwrite)
    else:
      c.Write()
      h.Write()
    f.Close()
    c.Close()
    del c
    del h

  except Exception:
    print(traceback.format_exc())

