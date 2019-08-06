
require("lpSolve")
require("Matrix")

fn <- "temp.json"

prices <- rjson::fromJSON(file=fn)

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
  A <- Matrix(0,ncol=length(names(prices))+1,nrow=length(names(prices)))
  rownames(A) <- names(prices)
  colnames(A) <- c(names(prices),paste0(owncur,"->",owncur))

  r <- "^(.*)->(.*)\\$(.*)#(.*)<->(.*)$"

  for (k in rownames(A)) {
    A[k,k] <- 1
  }

  S <- rep("<=",nrow(A))

  RHS <- numeric(nrow(A))
  fr <- gsub(r,"\\1",rownames(A))
  base <- gsub(r,"\\3",rownames(A))
  vl <- as.numeric(gsub(r,"\\4",rownames(A)))
  vr <- as.numeric(gsub(r,"\\5",rownames(A)))
  RHS[fr==base] <- (vr-vl)[fr==base]
  RHS[fr!=base] <- as.numeric(prices[fr!=base])*((vr-vl)[fr!=base])

  idx <- RHS!=Inf
  A <- A[idx,]
  S <- S[idx]
  RHS <- RHS[idx]

  list("A"=A,"S"=S,"RHS"=RHS)
}

bound_solution_constraint <- function(prices,owncur="ZEUR",bound=100)
{
  A <- Matrix(0,
              ncol=length(names(prices))+1,
              nrow=1)
  x <- paste0(owncur,"->",owncur)
  rownames(A) <- x
  colnames(A) <- c(names(prices),x)

  A[x,x] <- 1

  S <- "<="
  RHS <- bound

  list("A"=A,"S"=S,"RHS"=RHS)
}

objective_function <- function(prices,owncur)
{
  res <- numeric(length(names(prices))+1)
  x <- paste0(owncur,"->",owncur)
  names(res) <- c(names(prices),x)
  res[x] <- 1
  res
}

owncur <- "ZEUR"
upperlimit <- 100

l1 <- exchange_constraints(prices)
l2 <- volume_constraints(prices)
l3 <- bound_solution_constraint(prices,owncur=owncur,bound=upperlimit)
objective <- objective_function(prices,owncur=owncur)

A <- rbind(l1$A,l2$A,l3$A)
S <- c(l1$S,l2$S,l3$S)
RHS <- c(l1$RHS,l2$RHS,l3$RHS)

# solve linear optimisation
res <- lp(direction="max",
          objective.in=objective,
          const.mat=A,
          const.rhs=RHS,
          const.dir=S)

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

