import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_PHOTOS_DIR = path.join(__dirname, '../public/project-photos');
const OUTPUT_FILE = path.join(__dirname, '../public/project-photos.manifest.json');

const SUPPORTED_EXTENSIONS = ['.svg', '.jpg', '.jpeg', '.png', '.webp', '.avif'];
const SVG_FALLBACK_ONLY = true;
const EXCLUDE_FILES = ['placeholder.svg', '.DS_Store'];

interface ImageVariant {
  src: string;
  width: number;
  format: string;
}

interface ImageWithVariants {
  original: string;
  variants: ImageVariant[];
}

interface ProjectPhotosManifest {
  [projectId: string]: ImageWithVariants[];
}

function generateManifest(): void {
  console.log('scanning project photos...');

  if (!fs.existsSync(PROJECT_PHOTOS_DIR)) {
    console.error(`directory not found: ${PROJECT_PHOTOS_DIR}`);
    process.exit(1);
  }

  const manifest: ProjectPhotosManifest = {};
  const entries = fs.readdirSync(PROJECT_PHOTOS_DIR, { withFileTypes: true });

  // only filter directories and get the numerical IDs
  const projectFolders = entries
    .filter(entry => entry.isDirectory())
    .filter(entry => /^\d+$/.test(entry.name))
    .sort((a, b) => parseInt(a.name) - parseInt(b.name));

  console.log(`${projectFolders.length} project folders found`);

  for (const folder of projectFolders) {
    const projectId = folder.name;
    const folderPath = path.join(PROJECT_PHOTOS_DIR, projectId);
    const imageGroups = new Map<string, ImageWithVariants>();

    try {
      const files = fs.readdirSync(folderPath);
      
      for (const file of files) {
        const ext = path.extname(file).toLowerCase();
        
        // is it a supported extension and not excluded?
        if (SUPPORTED_EXTENSIONS.includes(ext) && !EXCLUDE_FILES.includes(file)) {
          const filePath = path.join(folderPath, file);
          const stats = fs.statSync(filePath);
          
          if (stats.isFile()) {
            const fileName = path.basename(file, ext);
            
            // is it a variant or original?
            const variantMatch = fileName.match(/^(.+)-(\d+)$/);
            
            if (variantMatch) {
              // it is a variant 
              const baseName = variantMatch[1];
              const width = parseInt(variantMatch[2]);
              const format = ext.replace('.', '');
              
              if (!imageGroups.has(baseName)) {
                imageGroups.set(baseName, {
                  original: '',
                  variants: [],
                });
              }
              
              const group = imageGroups.get(baseName)!;
              group.variants.push({
                src: `/project-photos/${projectId}/${file}`,
                width,
                format,
              });
            } else {
              // it is the original file 
              if (!imageGroups.has(fileName)) {
                imageGroups.set(fileName, {
                  original: `/project-photos/${projectId}/${file}`,
                  variants: [],
                });
              } else {
                // if it is already added, only update if it is not an SVG
                // keep the SVG as fallback but prioritize the variants
                const existing = imageGroups.get(fileName)!;
                if (ext !== '.svg' || existing.original === '') {
                  existing.original = `/project-photos/${projectId}/${file}`;
                }
              }
            }
          }
        }
      }

      // convert the map to an array and sort it
      const sortedImages = Array.from(imageGroups.entries())
        .sort((a, b) => {
          const numA = parseInt(a[0].match(/\d+/)?.[0] || '0');
          const numB = parseInt(b[0].match(/\d+/)?.[0] || '0');
          return numA - numB;
        })
        .map(([_, imageData]) => {
          // sort the variants by format and width
          imageData.variants.sort((a, b) => {
            // first format (avif > webp > other)
            const formatOrder = { avif: 0, webp: 1 };
            const orderA = formatOrder[a.format as keyof typeof formatOrder] ?? 2;
            const orderB = formatOrder[b.format as keyof typeof formatOrder] ?? 2;
            if (orderA !== orderB) return orderA - orderB;
            // then width
            return a.width - b.width;
          });
          return imageData;
        });

      manifest[projectId] = sortedImages;
      
      if (sortedImages.length > 0) {
        const totalVariants = sortedImages.reduce((sum, img) => sum + img.variants.length, 0);
        console.log(`  ✓ project ${projectId}: ${sortedImages.length} images, ${totalVariants} variants`);
      } else {
        console.log(`  ⚠ project ${projectId}: empty folder (placeholder will be used)`);
      }
    } catch (error) {
      console.error(`  ❌ project ${projectId} while scanning: ${error}`);
      manifest[projectId] = [];
    }
  }

  // write the manifest file
  // yapıyoruz kızlarımla manifest
  try {
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(manifest, null, 2), 'utf-8');
    console.log(`\n✅ manifest created: ${OUTPUT_FILE}`);
    console.log(`total ${Object.keys(manifest).length} projects saved in the manifest`);
  } catch (error) {
    console.error('❌ while writing manifest:', error);
    process.exit(1);
  }
}

// run 
generateManifest();

