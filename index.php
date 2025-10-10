<?php
$search = $_GET['search'] ?? '';
$cwd = getcwd();
$relPath = $_SERVER['REQUEST_URI'];
$pathParts = array_filter(explode('/', $relPath));

$subdirs = array_filter(glob('*'), 'is_dir');
$files = array_filter(glob('*'), 'is_file');

function is_plot($f) {
    return preg_match('/\.(png|jpe?g|gif|pdf)$/i', $f);
}
function matches_search($f, $search) {
    return empty($search) || stripos($f, $search) !== false;
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
  <meta http-equiv="Pragma" content="no-cache"/>
  <meta http-equiv="Expires" content="0"/>
  <title><?php echo basename($cwd); ?></title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
  <style>
    body > .container-fluid { margin-top: 20px; padding: 0 20px; }
    .empty-text { font-style: italic; font-size: 0.9rem; }
    #plot-listing .card { margin: 5px; max-width: 240px; }
    .card-img-top { max-height: 180px; object-fit: contain; }
  </style>
</head>
<body>
  <!-- Breadcrumb navigation -->
  <nav class="navbar navbar-light bg-light border-bottom">
	<div class="d-flex align-items-center">
	  <a href="/" class="text-decoration-none" style="color: blue;"><i class="bi bi-house-door"></i></a>

	  <?php
	    $uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
	    $parts = explode('/', trim($uri, '/'));
	    $accum = '';
	    foreach ($parts as $i => $part) {
		$accum .= '/' . $part;
		echo '<span class="mx-2">/</span>';
		if ($i < count($parts) - 1) {
		    echo '<a href="' . htmlspecialchars($accum) . '" class="text-decoration-none" style="color: blue;">' . htmlspecialchars($part) . '</a>';
		} else {
		    echo '<span class="fw-light" style="color: blue;">' . htmlspecialchars($part) . '</span>';
		}
	    }
	  ?>
	</div>
      <form class="d-flex" method="get">
        <input class="form-control me-2" type="search" name="search" placeholder="Pattern(s)" value="<?php echo htmlspecialchars($search); ?>">
        <button class="btn btn-outline-success" type="submit">Search</button>
      </form>
    </div>
  </nav>

  <div class="container-fluid">
    <!-- Subdirectories -->
    <h5 class="mt-4">Directories</h5>
    <?php if (!empty($subdirs)): ?>
      <ul>
        <?php foreach ($subdirs as $dir): ?>
          <?php if (matches_search($dir, $search)): ?>
            <li><a href="<?php echo htmlspecialchars($dir); ?>"><?php echo htmlspecialchars($dir); ?></a></li>
          <?php endif; ?>
        <?php endforeach; ?>
      </ul>
    <?php else: ?>
      <p class="empty-text">No directories found.</p>
    <?php endif; ?>

    <!-- Plots -->
	<h5 class="mt-4">Plots</h5>
	<div class="d-flex flex-wrap" id="plot-listing">
	<?php
	$displayed = [];
	$formats = ['png', 'pdf', 'root', 'C', 'jpg', 'jpeg', 'gif']; // include C and others

	foreach ($files as $file) {
	    if (!is_plot($file) && !preg_match('/\.(C)$/i', $file)) continue;
	    if (!matches_search($file, $search)) continue;

	    $ext = pathinfo($file, PATHINFO_EXTENSION);
	    $base = preg_replace('/\.(png|jpe?g|gif|pdf|root|C)$/i', '', $file);

	    if (in_array($base, $displayed)) continue;

	    // Collect all formats for this base
	    $available = [];
	    foreach ($formats as $fmt) {
		$candidate = $base . '.' . $fmt;
		if (file_exists($candidate)) {
		    $available[$fmt] = $candidate;
		}
	    }

	    // Show only if there's an image to display
	    $thumb = $available['png'] ?? null;
	    if (!$thumb) continue;

	    $displayed[] = $base;

	    $displayed[] = $base;
	    $root_path = $available['root'] ?? null;
            $div_id    = 'jsroot_' . md5($base);          // stable unique id per base
	    $baseName = basename($base);

	    echo '<div class="card">';
	    echo '<a href="' . htmlspecialchars($thumb) . '" target="_blank">';
	    echo '<div class="card-header text-danger fw-bold text-center">' . htmlspecialchars($baseName) . '</div>';
	    echo '<img src="' . htmlspecialchars($thumb) . '" class="card-img-top" alt="' . $thumb . '">';
	    echo '</a>';

	    echo '<div class="card-footer text-center">';
	    foreach ($available as $fmt => $path) {
		$color = match(strtolower($fmt)) {
		    'png' => 'primary',
		    'pdf' => 'danger',
		    'root' => 'dark',
		    'c' => 'success',
		    'jpg', 'jpeg' => 'warning',
		    'gif' => 'info',
		    default => 'secondary',
		};
		    // normal format link (download/view)
		$path_url = dirname($path) . '/' . rawurlencode(basename($path));
		// normal format link (download/view)
		echo '<a class="btn btn-sm btn-' . $color . ' mx-1" href="' . htmlspecialchars($path_url) . '" target="_blank" rel="noopener">'
   		. strtoupper($fmt) . '</a>';
		#echo '<a href="' . htmlspecialchars($path) . '" target="_blank" class="badge bg-' . $color . ' mx-1 text-decoration-none">' . htmlspecialchars($fmt) . '</a>';
		if (strtolower($fmt) === 'root') {
    			$default_obj = ''; // or e.g. $baseName . '_canvas'
    			$viewer = 'jsroot_viewer.php'
            		. '?file=' . rawurlencode(basename($path)) // only the filename, same dir
            		. '&obj='  . rawurlencode($default_obj);

    			echo '<a class="btn btn-sm btn-outline-dark mx-1"'
       			. ' href="' . htmlspecialchars($viewer) . '"'
       			. ' target="_blank" rel="noopener">[JSROOT]</a>';
	    }
	    }

		// --- ADD: container for the interactive canvas (hidden by default) ---
	    if ($root_path) {
    			echo '<div id="' . htmlspecialchars($div_id) . '" class="jsroot-container" '
       			. 'style="display:none; margin-top:0.5rem; min-height:360px; border:1px dashed #ccc;"></div>';
	    }
	    #}
	    echo '</div></div>';
	}
	if (empty($displayed)) {
	    echo "<p class='empty-text'>No plots to display</p>";
	}
	?>
	</div>

    <!-- Other Files -->
    <h5 class="mt-4">Other files</h5>
    <ul>
      <?php
      $displayed = array_map(fn($f) => $f . '.pdf', $displayed_basenames);  // files used as plots
      $others = array_filter($files, function($f) use ($displayed_basenames, $search) {
          return !is_plot($f) && matches_search($f, $search) && basename($f) !== 'index.php';
      });
      if (!empty($others)):
        foreach ($others as $f):
            echo "<li><a href=\"" . htmlspecialchars($f) . "\">" . htmlspecialchars($f) . "</a></li>";
        endforeach;
      else:
        echo "<p class='empty-text'>No files to display</p>";
      endif;
      ?>
    </ul>

    <!-- Scroll to Top -->
    <div class="text-start mt-3">
      <button id="scroll-top" class="btn btn-outline-primary btn-sm">To top</button>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    document.getElementById('scroll-top').onclick = () => window.scrollTo({top: 0, behavior: 'smooth'});
  </script>

  <script type="module">
    // Load once
    import * as JSROOT from 'https://root.cern/js/latest/modules/main.mjs';

    // Delegate clicks for any .jsroot-link present/added
    document.addEventListener('click', async (ev) => {
      const link = ev.target.closest('a.jsroot-link');
      if (!link) return;

      ev.preventDefault();

      const rootfile = link.dataset.rootfile;
      const objname  = (link.dataset.objname || '').trim();
      const divid    = link.dataset.divid;

      const container = document.getElementById(divid);
      if (!container) return;

      // Toggle visibility
      const showing = container.style.display !== 'none' && container.style.display !== '';
      if (showing) {
        container.style.display = 'none';
        return;
      }

      container.style.display = 'block';

      // Draw only once per container; remove this if you want to re-draw on each toggle
      if (container.dataset.drawn === '1') return;

      container.textContent = 'Loading ROOT file…';

      try {
        const file = await JSROOT.openFile(rootfile);

        // Pick object: use provided name if set, else auto-select first sensible object
        let targetPath = objname;

        if (!targetPath) {
          const keys = await file.readKeys(); // top-level keys
          // try common physics plot types in priority order
          const preferred = ['TCanvas','TH1','TH2','TGraph','TGraphErrors','TMultiGraph','RooHist','TProfile'];
          let picked = null;

          // helper: find first key whose _typename starts with any preferred type
          for (const pref of preferred) {
            picked = keys.find(k => (k && k._typename && k._typename.startsWith(pref)));
            if (picked) break;
          }
          // fallback to first key if nothing matched
          picked = picked || keys[0];

          if (!picked) throw new Error('No drawable objects found in ROOT file.');
          targetPath = picked.name; // name (with cycle is handled internally by JSROOT)
        }

        const obj = await file.readObject(targetPath);
        container.textContent = ''; // clear "Loading…" label
        await JSROOT.draw(container, obj, ''); // empty opts → default draw
        container.dataset.drawn = '1';
      } catch (e) {
        console.error(e);
        container.textContent = 'Failed to load/draw ROOT object.';
      }
    });
  </script>
</body>
</html>

