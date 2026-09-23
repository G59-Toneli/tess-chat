-- Papel de runtime da aplicação. Sem DDL; permissões por tabela vêm das migrações.
CREATE ROLE tess_app LOGIN PASSWORD 'tess_app';
GRANT CONNECT ON DATABASE tess TO tess_app;
GRANT USAGE ON SCHEMA public TO tess_app;
