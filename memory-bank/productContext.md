# Documentation Crawler & Semantic Search

## Purpose
This project creates a documentation crawler and semantic search system that enables Cline to efficiently access and search through API documentation. It automates the process of crawling documentation sites, extracting relevant content, and making it searchable through vector-based semantic search.

## Problem Statement
- Manual documentation lookup is time-consuming and inefficient
- Documentation content needs to be semantically searchable
- Documentation needs to be easily accessible through MCP tools

## Core Functionality
1. Documentation Crawling
   - Automated crawling of API documentation sites
   - Content extraction using Trafilatura
   - Support for structured API documentation formats

2. Semantic Search
   - Vector-based search using pgvector
   - OpenAI embeddings for semantic understanding
   - Relevance-based result ranking

3. MCP Integration
   - Tools for triggering documentation crawls
   - Semantic search capabilities
   - Easy access to documentation snippets

## Success Criteria
- Successfully crawl and index API documentation
- Provide accurate and relevant search results
- Enable efficient documentation access through MCP tools
- Support for bill.com API documentation as initial test case
