import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Utilitários para lidar com caminhos em ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, '../public');

/**
 * Cria e configura o servidor HTTP Vanilla
 */
export function createServer() {
  const server = http.createServer((req, res) => {
    // Rota simples para arquivos estáticos
    let filePath = path.join(PUBLIC_DIR, req.url === '/' ? 'index.html' : req.url);
    
    // Proteção básica contra travessia de diretório
    if (!filePath.startsWith(PUBLIC_DIR)) {
      res.writeHead(403);
      res.end('Acesso negado');
      return;
    }

    const extname = path.extname(filePath);
    let contentType = 'text/html';

    switch (extname) {
      case '.js': contentType = 'text/javascript'; break;
      case '.css': contentType = 'text/css'; break;
      case '.json': contentType = 'application/json'; break;
      case '.png': contentType = 'image/png'; break;
      case '.jpg': contentType = 'image/jpg'; break;
    }

    fs.readFile(filePath, (error, content) => {
      if (error) {
        if (error.code === 'ENOENT') {
          res.writeHead(404);
          res.end('Arquivo não encontrado');
        } else {
          res.writeHead(500);
          res.end(`Erro no servidor: ${error.code}`);
        }
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content, 'utf-8');
      }
    });
  });

  return {
    server,
    start: () => {
      server.listen(PORT, () => {
        console.log(`[HTTP] Servidor rodando em http://localhost:${PORT}`);
      });
    }
  };
}
