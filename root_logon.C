{
   TStyle *myStyle  = new TStyle("MyStyle", "My Root Styles");

   // from ROOT plain style
   myStyle->SetCanvasBorderMode(0);
   myStyle->SetPadBorderMode(0);
   myStyle->SetPadColor(0);
   myStyle->SetCanvasColor(0);
   myStyle->SetTitleColor(1);
   myStyle->SetStatColor(0);

   myStyle->SetHistLineWidth(2);
   myStyle->SetHistLineColor(kBlue+1);

   myStyle->SetLineWidth(1);

   //myStyle->SetLineStyleString(2,"[12 12]"); // postscript dashes
   //myStyle->SetErrorX(0.001);

   //myStyle->SetPadTickX(0);
   //myStyle->SetPadTickY(0);


   myStyle->SetFuncColor(kRed+1);
   myStyle->SetFuncWidth(3);
   //myStyle->SetLineColor(kRed+1);

   myStyle->SetTitleFont(62, "X");
   myStyle->SetTitleFont(62, "Y");

   myStyle->SetLabelSize(0.04, "X");
   myStyle->SetTitleSize(0.04, "X");

   myStyle->SetLabelSize(0.05, "Y");
   myStyle->SetTitleSize(0.05, "Y");

   myStyle->SetTitleOffset(1.3, "Y");
   myStyle->SetTitleOffset(1.1, "X");

   // default canvas positioning
//   myStyle->SetCanvasDefX(900);
//  myStyle->SetCanvasDefY(20);
   //myStyle->SetCanvasDefH(600);
   //myStyle->SetCanvasDefW(800);

   myStyle->SetPadBottomMargin(0.1);
   myStyle->SetPadTopMargin(0.1);
   myStyle->SetPadLeftMargin(0.2);
   myStyle->SetPadRightMargin(0.1);
   myStyle->SetPadTickX(1);
   myStyle->SetPadTickY(1);
   myStyle->SetFrameBorderMode(0);

   myStyle->SetTitleBorderSize(0);
   myStyle->SetOptTitle(0);

   // Din letter
//   myStyle->SetPaperSize(21, 28);

   myStyle->SetStatBorderSize(0);
   myStyle->SetStatColor(0);
   myStyle->SetStatX(0.85);
   myStyle->SetStatY(0.87);
   myStyle->SetStatFont(42);
   myStyle->SetStatFontSize(0.03);
   myStyle->SetOptStat(0);
   myStyle->SetOptFit(111);
   myStyle->SetPalette(1);

   // apply the new style
   gROOT->SetStyle("MyStyle"); //uncomment to set this style
   gROOT->ForceStyle(); // use this style, not the one saved in root files

}
