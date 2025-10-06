<?php
$filename = isset($_GET['file']) ? basename($_GET['file']) : '';
$objectname = pathinfo($filename, PATHINFO_FILENAME) . '_canvas';
?>
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>JSROOT View: <?php echo htmlspecialchars($filename); ?></title>
</head>
<body>
  <h2>JSROOT view of <?php echo htmlspecialchars($filename); ?></h2>
  <div id="drawing" style="width:800px; height:600px;"></div>

  <script type="module">
    import * as JSROOT from 'https://root.cern/js/latest/modules/main.mjs';

    const rootfile = <?php echo json_encode($filename); ?>;
    const objname = <?php echo json_encode($objectname); ?>;

    async function drawRoot() {
      try {
        let file = await JSROOT.openFile(rootfile);
        let obj = await file.readObject(objname);
        JSROOT.gStyle.PadRightMargin = 0.2;  // Optional customization
        JSROOT.draw('drawing', obj, '');     // Add draw options if needed
      } catch(e) {
        console.error(e);
        document.getElementById('drawing').textContent = 'Failed to load ROOT file or object.';
      }
    }

    drawRoot();
  </script>
</body>
</html>
