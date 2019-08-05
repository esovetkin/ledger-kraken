
require("lpSolve")
require("Matrix")

fn <- "temp.json"

read_depth_prices <- function(fn)
{
  prices <- rjson::fromJSON(file=fn)

  curs  <- unique(c(gsub("^([A-Za-z]*)->([A-Za-z]*)#(.*)<->(.*)$","\\1\\3\\4",names(X)),
                    gsub("^([A-Za-z]*)->([A-Za-z]*)#(.*)<->(.*)$","\\2\\3\\4",names(X))))


  return()
}

read_ticker_prices <- function(fn)
{
  data <- rjson::fromJSON(file=fn)

  pairs <- simplify2array(strsplit(names(X),split="->"))
  curs <- unique(as.character(pairs))

  data <- matrix(0,ncol=length(curs),nrow=length(curs))
  colnames(data) <- curs
  rownames(data) <- curs

  for (x in names(X)) {
    from <- strsplit(x,split="->")[[1]][1]
    to <- strsplit(x,split="->")[[1]][2]
    data[from,to] <- X[x][[1]]
  }

  for (x in curs)
    data[x,x] <- 1
}

exchange_constraints <- function(prices, owncur="ZEUR")
{
  r <- "^(.*)->(.*)\\$(.*)#(.*)<->(.*)$"
  curs <- unique(c(gsub(r,"\\1#\\4<->\\5",names(prices))))
  A <- Matrix(0,ncol=length(names(prices))+1,nrow=length(curs))
  rownames(A) <- curs
  colnames(A) <- c(names(prices),paste0(owncur,"->",owncur))

  for (k in names(prices)) {
    re <- "^(.*)->(.*)\\$(.*)#(.*)<->(.*)$"
    from <- gsub(re,"\\1",k)
    to <- gsub(re,"\\2",k)
    base <- gsub(re,"\\3",k)
    vl <- gsub(re,"\\4",k)
    vu <- gsub(re,"\\5",k)

    A[paste0(from,"#",vl,"<->",vu),k] = 1
    A[paste0(to,"#",vl,"<->",vu),k] = -prices[k][[1]]
  }

  S <- rep("=",nrow(A))
  RHS <- rep(0,nrow(A))

  list("A"=A,"S"=S,"RHS"=RHS)
}

volume_constraints <- function(prices,owncur="ZEUR")
{
  rows <- paste0(c("L!","U!"),sort(rep(names(prices),2)))
  A <- Matrix(0,ncol=length(names(prices))+1,nrow=length(rows))
  rownames(A) <- rows
  colnames(A) <- c(names(prices),paste0(owncur,"->",owncur))

  r <- "^([LU])!([A-Za-z]*->[A-Za-z]*#.*<->.*)$"

  for (k in rownames(A)) {
    A[k,gsub(r,"\\2",k)] <- 1
  }

  S <- character(nrow(A))
  x <- gsub(r,"\\1",rownames(A))
  S[x=="L"] <- "<="
  S[x=="U"] <- ">="

  r <- "^([LU])![A-Za-z]*->[A-Za-z]*#(.*)<->(.*)$"
  RHS <- numeric(nrow(A))
  x <- gsub(r,"\\1",rownames(A))
  l <- as.numeric(gsub(r,"\\2",rownames(A)))
  u <- as.numeric(gsub(r,"\\3",rownames(A)))
  RHS[x=="L"] <- l[x=="L"]
  RHS[x=="U"] <- u[x=="U"]

  idx <- RHS!=Inf
  list("A"=A[idx,],"S"=S[idx],"RHS"=RHS[idx])
}

l1 <- exchange_constraints(prices)
l2 <- volume_constraints(prices)

bound_solution_constraint <- function(prices,owncur="ZEUR",bound=100)
{
  A <- Matrix(0,
              ncol=length(names(prices)),
              nrow=1)
  rownames(A) <- "ZEUR->ZEUR"
  colnames(A) <- names(prices)


}


## # take subsample for debugging
## idx <- unique(c(sample(colnames(data),size=3),"EUR"))
## data <- data[idx,idx]

# currency owned
own.cur <- "ZEUR"
upper.limit <- 100

k <- ncol(data)

# constraints matrix, rhs, direction, objective function vector
const.mat <- matrix(0,ncol=k^2,nrow=k+1)
colnames(const.mat) <- as.character(outer(colnames(data),colnames(data),
                                          function(x,y) paste0(x,"->",y)))
rownames(const.mat) <- c("bounded_constr",rownames(data))

# right hand side for inequalities
const.rhs <- c(upper.limit,rep(0,k))
names(const.rhs) <- c("bounded_constr",colnames(data))

# constraint directions
const.dir <- c("<=",rep("=",k))

# objective function vector
objective.in <- c(rep(0,k^2))
names(objective.in) <- colnames(const.mat)
objective.in[paste0(own.cur,"->",own.cur)] <- 1

# fill constaint matrix with elements
const.mat[1,paste0(own.cur,"->",own.cur)] <- 1

for (row in rownames(const.mat)[-1]) {
  # columns for A part
  idx.A <- colnames(const.mat)[grep(paste0(row,"->.*"),colnames(const.mat))]
  # columns for B part
  idx.B <- colnames(const.mat)[grep(paste0(".*->",row),colnames(const.mat))]

  # index for exchange rates
  idx.price <- simplify2array(strsplit(idx.B,split="->"))

  # fill const.mat
  const.mat[row,idx.B] <- -data[unique(idx.price[1,]),unique(idx.price[2,])]
  const.mat[row,idx.A] <- 1

  # fix diagonal element
  if (own.cur == row) next

  const.mat[row,paste0(row,"->",row)] <- 0
}

# solve linear optimisation
res <- lp(direction="max",
          objective.in=objective.in,
          const.mat=const.mat,
          const.rhs=const.rhs,
          const.dir=const.dir)

# obtain strategy
strategy <- res$solution
names(strategy) <- colnames(const.mat)

strategy[0!=strategy]

# print strategy in the ordered way (this will not work in general solution though)
s <- strategy[0!=strategy]
order <- numeric(length(s))
i <- 1
cur <- own.cur
while (i < length(s)) {
  idx <- grepl(paste0(cur,"->.*"),names(s)) & (!grepl(paste0(cur,"->",cur),names(s)))
  order[idx] <- i
  i <- i+1
  cur <- gsub(paste0(cur,"->(.*)"),"\\1",names(s)[idx])
}
s[order(order)]

cur <- names(s[order(order)])
cur <- unique(unlist(strsplit(cur,"->")))

data[cur,cur]

interest <- 1 + strategy["ZEUR->ZEUR"]/
  (sum(strategy[grep("ZEUR->.*",x=names(strategy))])-strategy["ZEUR->ZEUR"])
interest

