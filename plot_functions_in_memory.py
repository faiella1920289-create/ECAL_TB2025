
import time, re, os, ROOT, sys
import numpy as np
import traceback
import shutil

def plot_chunk(args):
    """
    Wrapper to handle chunking for multiprocessing.
    """
    plotconf_df, arrays, plot_output_folder, kwargs = args

    plotconf_df.apply(lambda row: plot(row, arrays, plot_output_folder, **kwargs), axis=1)

def replace_index_axis1(match):
    var = match.group(1)
    idx = match.group(2)
    return f"uproot_dict['{var}'][:,{idx}]"

def replace_index_noch(match):
    var = match.group(1)
    return f"uproot_dict['{var}']"

def eval_formula(formula, data_dict):
    if "((" in formula:
      pattern = re.compile(r"\(\(\s*(\w+)\s*\)\)")
      numpy_expr = pattern.sub(replace_index_noch, formula)
      print(numpy_expr, file=sys.stderr, flush=True)

      result = eval(numpy_expr, {"uproot_dict": data_dict, "np": np})

      return result


    if "[" not in formula: return data_dict[formula]

    #if "[" not in formula: eval(formula, {"uproot_dict": data_dict, "np": np})

    pattern = re.compile(r"(\w+)\[(\d+)\]")
    numpy_expr = pattern.sub(replace_index_axis1, formula)
    print(numpy_expr, file=sys.stderr, flush=True)
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
        # pattern = rf'(?<!\()([^\s&|()]+(?:\s*\[[^\]]+\])?\s*{re.escape(op)}\s*[+-]?\d*\.?\d*(?:e[+-]?\d+)?|[^\s&|()]+)(?!\))'
        expr = re.sub(pattern, r'(\1)', expr)

    return expr


def draw_TT_grid(hist, c):
    c.cd()
    lines = []
    line_color = ROOT.kBlack
    line_style = 1
    line_width = 1
    x_min = hist.GetXaxis().GetXmin()
    x_max = hist.GetXaxis().GetXmax()
    y_min = hist.GetYaxis().GetXmin()
    y_max = hist.GetYaxis().GetXmax()

    # vertical grid lines
    for i in range(1, 66, 5):
      x = i - 0.5
      line = ROOT.TLine(x, y_min, x, y_max)
      line.SetLineColor(line_color)
      line.SetLineStyle(line_style)
      line.SetLineWidth(line_width)
      line.Draw("same")
      lines.append(line)  

    # horizontal grid lines
    for j in range(1, 11, 5):
      y = j - 0.5
      line = ROOT.TLine(x_min, y, x_max, y)
      line.SetLineColor(line_color)
      line.SetLineStyle(line_style)
      line.SetLineWidth(line_width)
      line.Draw("same")
      lines.append(line)
    return lines  

# def convert_root_cut_to_numpy_expr(cut_str, available_vars):
#     # 1. ROOT → NumPy logical operators
#     cut_str = cut_str.replace("&&", "&").replace("||", "|")

#     # 2. Rimuovi spazi inutili
#     cut_str = cut_str.strip()

#     # 3. Proteggi le variabili per evitare risostituzioni
#     for var in sorted(available_vars, key=len, reverse=True):
#         pattern = r'\b' + re.escape(var) + r'\b'
#         cut_str = re.sub(pattern, f'@@VAR_{var}@@', cut_str)

#     # 4. Ripristina come uproot_dict["var"]
#     for var in available_vars:
#         cut_str = cut_str.replace(f'@@VAR_{var}@@', f'uproot_dict["{var}"]')

#     # 5. Rendi espliciti i numeri negativi: inserisci spazio prima del segno meno se serve
#     cut_str = re.sub(r'(?<==)-', ' -', cut_str)

#     # 6. Aggiungi parentesi ai confronti (>=, <=, ==, !=, >, <)
#     comp_ops = ['>=', '<=', '==', '!=', '>', '<']
#     for op in comp_ops:
#         # match espressioni come uproot_dict["x"]== -1 oppure >=3
#         pattern = rf'(?<!\()(\s*uproot_dict\["[^"]+"\]\s*{re.escape(op)}\s*-?\d*\.?\d*(?:e[+-]?\d+)?)(?!\))'
#         cut_str = re.sub(pattern, r'(\1)', cut_str)

#     return cut_str


def plot(row, uproot_dict, outputfolder, just_draw=False):

  try:
    os.makedirs(f"{outputfolder}/{row.folder}/", exist_ok=True)

    if not os.path.exists(f"{outputfolder}/{row.folder}/index.php"):
      shutil.copy2(f"{outputfolder}/index.php", f"{outputfolder}/{row.folder}/index.php")
    if not os.path.exists(f"{outputfolder}/{row.folder}/jsroot_viewer.php"):
      shutil.copy2(f"{outputfolder}/jsroot_viewer.php", f"{outputfolder}/{row.folder}/jsroot_viewer.php")
  except Exception:
    print(traceback.format_exc(), file=sys.stderr, flush=True)

  ROOT.gErrorIgnoreLevel = ROOT.kError

  print(f"outputfolder: {outputfolder}", file=sys.stderr, flush=True)

  time_start = time.time()

  try:
    name = row['name']

    print(name, file=sys.stderr, flush=True)

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

        c.Update()
        max_bin = h.GetMaximumBin()
        max_position = h.GetBinCenter(max_bin)
        max_value = h.GetBinContent(max_bin)
        bin1 = h.FindFirstBinAbove(max_value/2)
        bin2 = h.FindLastBinAbove(max_value/2)
        fwhm = h.GetBinCenter(bin2) - h.GetBinCenter(bin1)

        pave = ROOT.TPaveText(0.65, 0.7, 0.85, 0.88, "NDC")
        pave.SetFillColor(0)  # Transparent background
        pave.SetTextFont(42)
        pave.SetTextSize(0.03)
        pave.SetBorderSize(0)

        # add three lines
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
          print("x.shape: ", x.shape, flush=True)
          print("y.shape: ", y.shape, flush=True)
          h.FillN(len(x), x.astype(np.float64), y.astype(np.float64), np.ones_like(x, dtype=np.float64))

        h.Draw("ZCOL")
        h.GetYaxis().SetTitle(row.ylabel)

    else:
        ROOT.gStyle.SetPalette(ROOT.kLightTemperature)
        if just_draw:
          h = f.Get(f"{name}")
        else:
          y_notflat = eval_formula(row.y, uproot_dict)[mask]
          n_ch = y_notflat.shape[1]
          y = y_notflat.ravel()
          z = eval_formula(row.z, uproot_dict)[mask].ravel()

          h = ROOT.TH2D(name, row.title,
                            int(row.binsnx), float(row.binsminx), float(row.binsmaxx),
                            int(row.binsny), float(row.binsminy), float(row.binsmaxy))

          h.FillN(len(x),
                x.astype(np.float64),
                y.astype(np.float64),
                z.astype(np.float64)*n_ch)

        h.Scale(1/h.GetEntries())
        h.Draw("ZCOL")

        # 5x5 grid fot TTs
        if row.tt:
          lines = draw_TT_grid(h, c)

        h.SetContour(int(row.contours))
        h.GetZaxis().SetTitle(row.zlabel)
        h.GetYaxis().SetTitle(row.ylabel)
        h.GetXaxis().SetNdivisions(505)
        h.GetYaxis().SetNdivisions(505)
        c.SetRightMargin(0.18)

    h.GetXaxis().SetTitle(row.xlabel)


    c.SaveAs(f"{outputfolder}/{row.folder}/{name}.png")
    if just_draw: c.Write("", ROOT.TObject.kOverwrite)
    else:
      c.Write()
      if str(row.y).strip() != "0" and str(row.z).strip() != "0": h.Scale(h.GetEntries())
      h.Write()
    f.Close()
    c.Close()
    del c
    del h

    print(f"{name} took {time.time() - time_start:.1f}s", file=sys.stderr, flush=True)
  except Exception:
    print(traceback.format_exc(), file=sys.stderr, flush=True)

