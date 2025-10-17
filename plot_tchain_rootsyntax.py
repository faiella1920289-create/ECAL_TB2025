#python3

#questo fa un dataset solo (anche molti file) ma una sola tchain

#va chiamato da un'altro programma lasciando plot.conf costante e variando data.conf per fare tutti i dataset in batch con gli stessi plot e gli stessi tagli

import ROOT
import sys
import pandas as pd
import os
import argparse

parser = argparse.ArgumentParser(description='Online monitor and reconstruction for crilin July')

parser.add_argument('plotconffile', type=str, help='plotconffile')
parser.add_argument('files_wildcard', type=str, help='fileswildcard')
parser.add_argument('outputfolder', type=str, help='outfolder')

args = parser.parse_args()
v = vars(args)
print(v)
vars().update(v)

macro = ["root_logon.C"] #x elisa: root logon

def plot(row, chain, outputfolder):
  name = row['name']
  print(f"{outputfolder}/{name}.root")
  f = ROOT.TFile(f"{outputfolder}/{name}.root", "recreate")
  f.cd()
  c = ROOT.TCanvas(f"{name}_canvas")
  c.cd()
  if str(row.cuts).strip() == "": cut = "1"
  else: cut = str(row.cuts)
  if str(row.y).strip()=="0":
    h = ROOT.TH1F(f"{name}", f"{row.title}", int(row.binsnx), float(row.binsminx), float(row.binsmaxx))
    chain.Draw(f"{row.x}>>{name}", f"{cut}")
    print(f"DEBUG ---- {row.x}>>{name}, {cut}")
    h.SetLineColor(eval(f"ROOT.{row.color}"))
    binw = (float(row.binsmaxx) - float(row.binsminx))/int(row.binsnx)
    h.GetYaxis().SetTitle(f"Entries / {float(f'{binw:.1g}'):g} {row.ylabel}")
  else:
    print("profilex: ", row.profilex)
    hh = ROOT.TH2F(f"{name}", f"{row.title}", int(row.binsnx), float(row.binsminx), float(row.binsmaxx), int(row.binsny), float(row.binsminy), float(row.binsmaxy))
    chain.Draw(f"{row.y}:{row.x}>>{name}", f"{cut}", "zcol")
    if not row.profilex: h = hh
    else:
      h = hh.ProfileX(f"prof_{name}")
      c.cd()
      h.Draw("prof")
    h.GetYaxis().SetTitle(f"{row.ylabel}")
  h.GetXaxis().SetTitle(f"{row.xlabel}")
  c.SaveAs(f"{outputfolder}/{name}.pdf")
  c.SaveAs(f"{outputfolder}/{name}.png")
  c.Write()
  h.Write()
  f.Close()
  c.Close()
  del c
  del h

for m in macro: ROOT.gROOT.LoadMacro(m)

plotconf_df = pd.read_csv(plotconffile, sep=",", comment="#")

os.system(f"cp index.php {outputfolder}")
os.system(f"cp jsroot_viewer.php {outputfolder}")

chain = ROOT.TChain("tree")
chain.Add(files_wildcard)
os.system(f"mkdir {outputfolder}/")
os.system(f"cp index.php {outputfolder}/")
plotconf_df.apply(lambda plotrow: plot(plotrow, chain, f"{outputfolder}/"), axis=1)
